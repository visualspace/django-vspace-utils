from django.db import models


def get_next_ordering(model, field_name='sort_order', increment=10):
    """
    Get the next available value for the sortorder for a model.

    Use case::

        class MyModel(models.Model):
            sort_order = models.PositiveSmallIntegerField(
                default=lambda: get_next_ordering(MyModel)
            )

    """
    aggregate = model.objects.aggregate(latest=models.Max(field_name))
    latest = aggregate['latest']

    if latest:
        return latest + increment
    else:
        return increment
