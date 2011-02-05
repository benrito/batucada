import logging
import datetime
import random
import string
import hashlib
import os

from django.db import models
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from taggit.models import GenericTaggedItemBase, Tag
from taggit.managers import TaggableManager

from drumbeat import storage
from drumbeat.utils import get_partition_id, safe_filename
from drumbeat.models import ModelBase
from relationships.models import Relationship
from projects.models import Project
from users import tasks
from broadcasts.models import Broadcast

import caching.base

log = logging.getLogger(__name__)


def determine_upload_path(instance, filename):
    chunk_size = 1000  # max files per directory
    return "images/profiles/%(partition)d/%(filename)s" % {
        'partition': get_partition_id(instance.pk, chunk_size),
        'filename': safe_filename(filename),
    }


def get_hexdigest(algorithm, salt, raw_password):
    """Generate password hash."""
    return hashlib.new(algorithm, smart_str(salt + raw_password)).hexdigest()


def create_password(algorithm, raw_password):
    """Create salted, hashed password."""
    salt = os.urandom(5).encode('hex')
    hsh = get_hexdigest(algorithm, salt, raw_password)
    return '$'.join((algorithm, salt, hsh))


class ProfileTag(Tag):
    CATEGORY_CHOICES = (
        ('skill', 'Skill'),
        ('interest', 'Interest'),
    )
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)


class TaggedProfile(GenericTaggedItemBase):
    tag = models.ForeignKey(
        ProfileTag, related_name="%(app_label)s_%(class)s_items")

    class Meta:
        verbose_name = "Tagged User Profile"
        verbose_name_plural = "Tagged User Profiles"


class UserProfileManager(caching.base.CachingManager):

    def get_popular(self, limit=0):
        users = Relationship.objects.values('target_user_id').annotate(
            models.Count('id')).filter(target_user__featured=False).order_by(
            '-id__count')[:limit]
        user_ids = [u['target_user_id'] for u in users]
        return UserProfile.objects.filter(id__in=user_ids)


class UserProfile(ModelBase):
    """Each user gets a profile."""
    object_type = 'http://activitystrea.ms/schema/1.0/person'

    username = models.CharField(max_length=255, default='', unique=True)
    display_name = models.CharField(
        max_length=255, default='', null=True, blank=True)
    password = models.CharField(max_length=255, default='')
    email = models.EmailField(unique=True, null=True)
    bio = models.TextField(blank=True, default='')
    image = models.ImageField(
        upload_to=determine_upload_path, default='', blank=True, null=True,
        storage=storage.ImageStorage())
    confirmation_code = models.CharField(
        max_length=255, default='', blank=True)
    location = models.CharField(max_length=255, blank=True, default='')
    featured = models.BooleanField()
    newsletter = models.BooleanField()
    disabled_broadcasts = models.TextField(
        blank=True, default='', editable=False)

    created_on = models.DateTimeField(
        auto_now_add=True, default=datetime.date.today())

    user = models.ForeignKey(User, null=True, editable=False, blank=True)
    tags = TaggableManager(through=TaggedProfile)

    objects = UserProfileManager()

    def __unicode__(self):
        return self.display_name or self.username

    def get_broadcasts(self):
        if not self.disabled_broadcasts:
            return Broadcast.objects.all()
        try:
            disabled = simplejson.loads(self.disabled_broadcasts)
            if isinstance(disabled, dict):
                return Broadcast.objects.exclude(id__in=disabled.keys())
        except:
            pass
        return None

    def following(self, model=None):
        """
        Return a list of objects this user is following. All objects returned
        will be ```Project``` or ```UserProfile``` instances. Optionally filter
        by type by including a ```model``` parameter.
        """
        if isinstance(model, Project) or model == Project:
            relationships = Relationship.objects.select_related(
                'target_project').filter(source=self).exclude(
                target_project__isnull=True)
            return [rel.target_project for rel in relationships]
        relationships = Relationship.objects.select_related(
            'target_user').filter(source=self).exclude(
            target_user__isnull=True)
        return [rel.target_user for rel in relationships]

    def followers(self):
        """Return a list of this users followers."""
        relationships = Relationship.objects.select_related(
            'source').filter(target_user=self)
        return [rel.source for rel in relationships]

    def is_following(self, model):
        """Determine whether this user is following ```model```."""
        return model in self.following(model=model)

    @models.permalink
    def get_absolute_url(self):
        return ('users_profile_view', (), {
            'username': self.username,
        })

    def create_django_user(self):
        """Make a django.contrib.auth.models.User for this UserProfile."""
        self.user = User(id=self.pk)
        self.user.username = self.username
        self.user.email = self.email
        self.user.date_joined = self.created_on
        self.user.backend = 'django.contrib.auth.backends.ModelBackend'
        self.user.save()
        self.save()
        return self.user

    def email_confirmation_code(self, url):
        """Send a confirmation email to the user after registering."""
        body = render_to_string('users/emails/registration_confirm.txt', {
            'confirmation_url': url,
        })
        subject = _('Complete Registration')
        tasks.SendUserEmail.apply_async(args=(self, subject, body))

    def image_or_default(self):
        """Return user profile image or a default."""
        return self.image or 'images/member-missing.png'

    def generate_confirmation_code(self):
        if not self.confirmation_code:
            self.confirmation_code = ''.join(random.sample(string.letters +
                                                           string.digits, 60))
        return self.confirmation_code

    def set_password(self, raw_password, algorithm='sha512'):
        self.password = create_password(algorithm, raw_password)

    def check_password(self, raw_password):
        if '$' not in self.password:
            valid = (get_hexdigest('md5', '', raw_password) == self.password)
            if valid:
                # Upgrade an old password.
                self.set_password(raw_password)
                self.save()
            return valid

        algo, salt, hsh = self.password.split('$')
        return hsh == get_hexdigest(algo, salt, raw_password)

    @property
    def name(self):
        return self.display_name or self.username
