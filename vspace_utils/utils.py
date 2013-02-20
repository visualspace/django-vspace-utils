import logging
logger = logging.getLogger(__name__)

from django.db import models


def get_next_ordering(model_or_qs, field_name='sort_order', increment=10):
    """
    Get the next available value for the sortorder for a model.

    Use case::

        class MyModel(models.Model):
            sort_order = models.PositiveSmallIntegerField(
                default=lambda: get_next_ordering(MyModel)
            )

    """
    if isinstance(model_or_qs, models.base.ModelBase):
        # If a model has been given, create QuerySet for all objects
        qs = model_or_qs.objects.all()
    else:
        # No model has been given, assert that the input is in fact
        # a QuerySet.
        assert isinstance(model_or_qs, models.query.QuerySet)
        qs = model_or_qs

    aggregate = qs.aggregate(latest=models.Max(field_name))
    latest = aggregate['latest']

    if latest:
        return latest + increment
    else:
        return increment


def get_or_create_object(model, **kwargs):
    """
    Get or create feed entry with specified kwargs without saving.

    This behaves like Django's own get_or_create but it doesn't save the
    newly created object, allowing for further modification before saving
    without triggering an extra `save()` call.
    """

    try:
        # Updating an existing object
        db_entry = model.objects.get(**kwargs)

        logger.debug('Updating existing entry %s', db_entry)

    except model.DoesNotExist:
        # Creating a new object
        db_entry = model(**kwargs)

        logger.debug('Creating new entry %s', db_entry)

    return db_entry
