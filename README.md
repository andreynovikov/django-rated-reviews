# Rated reviews application for Django

[![Test status](https://github.com/andreynovikov/django-rated-reviews/actions/workflows/test.yaml/badge.svg)](https://github.com/andreynovikov/django-rated-reviews/actions/workflows/test.yaml)
[![Documentation Status](https://img.shields.io/readthedocs/django-rated-reviews.svg?style=flat)](https://readthedocs.org/projects/django-rated-reviews/)
[![GitHub release](https://img.shields.io/github/release/andreynovikov/django-rated-reviews.svg)](https://github.com/andreynovikov/django-rated-reviews/releases/latest)
[![PyPI release](https://img.shields.io/pypi/v/django-rated-reviews.svg)](https://pypi.org/project/django-rated-reviews/)
[![Python version](https://img.shields.io/pypi/pyversions/django-rated-reviews.svg)](https://pypi.org/project/django-rated-reviews/)
[![GitHub issues](https://img.shields.io/github/issues/andreynovikov/django-rated-reviews.svg)](https://github.com/andreynovikov/django-rated-reviews/issues)
[![GitHub license](https://img.shields.io/github/license/andreynovikov/django-rated-reviews.svg)](LICENSE)

Rated reviews is derived from [Django “excontrib” Comments](https://github.com/django/django-contrib-comments/) and can be used to attach reviews with rating to any model. The core difference from comments is that user can provide only one review per item. Rating is expressed by a number and by default visualized with stars. However, it can be changed to whatever you want. Rating grades are also configurable.

Optionally rating can be weighted. For instance, you can designate experts whose rating would be more valuable. Alternatively, add weight to reviews of real byers of sold product.

Reviews can be used with Django templates or through optional REST API.

[Documentation is published](https://django-rated-reviews.readthedocs.io/) on Read the Docs.

## Requirements

* Python 3.10+
* Django 5.2+ (5.2, 6.0 and 6.1 are tested)
* `django.contrib.sites` framework
* Optional: [Django REST framework](https://www.django-rest-framework.org/) 3.16+ for REST API

## Installation

Install ```django-rated-reviews``` using pip:

```shell
pip install django-rated-reviews
```

Add ```reviews``` to ```INSTALLED_APPS```. Example:

```python
INSTALLED_APPS = (
    ...
    'django.contrib.sites',
    'reviews',
    ...
)
```

Run ```manage.py migrate``` so that Django will create the review tables.

Add the reviews app’s URLs to your project’s urls.py:

```python
urlpatterns = [
    ...
    path('reviews/', include('reviews.urls')),
    ...
]
```

Use the review template tags to embed reviews in your templates.

## REST API

REST API is optional and requires Django REST framework. Install it together with reviews:

```shell
pip install "django-rated-reviews[api]"
```

Add ```rest_framework``` to ```INSTALLED_APPS``` and register ```ReviewViewSet``` in a router:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reviews.api import ReviewViewSet

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'reviews/(?P<model>\w+\.\w+)/(?P<identifier>[^/.]+)', ReviewViewSet, basename='model-review')

urlpatterns = [
    ...
    path('api/', include(router.urls)),
    ...
]
```

Reviewed model is referenced as ```app_label.model_name``` (e.g. ```shop.product```) and reviewed object by its
primary key. Both can be passed in URL, as registered above, or as ```model``` and ```identifier``` query parameters:
```/api/reviews/shop.product/17/``` is the same as ```/api/reviews/?model=shop.product&identifier=17```.

| Method      | URL                                      | Description                                             | Permission    |
|-------------|------------------------------------------|---------------------------------------------------------|---------------|
| `GET`       | `/api/reviews/{model}/{identifier}/`         | Published reviews of an object with statistics          | Anyone        |
| `POST`      | `/api/reviews/{model}/{identifier}/`         | Post a review                                           | Authenticated |
| `GET`       | `/api/reviews/{model}/{identifier}/{id}/`    | Get a review                                            | Anyone        |
| `PUT`       | `/api/reviews/{model}/{identifier}/{id}/`    | Modify a review, it is moderated again                  | Review author |
| `DELETE`    | `/api/reviews/{model}/{identifier}/{id}/`    | Delete a review                                         | Staff         |
| `GET`       | `/api/reviews/{model}/{identifier}/average/` | Weighted average rating of an object                    | Anyone        |
| `GET`       | `/api/reviews/{model}/{identifier}/form/`    | Review form fields, including security fields           | Anyone        |
| `GET`       | `/api/reviews/?model={model}`                | Published reviews of all objects of a model             | Anyone        |

Review lists are paginated and can be filtered by review model fields, e.g. ```?rating=5```, ```?rating=4&rating=5```
or ```?user=12```. Review list of an object also contains weighted average rating with number of reviews per rating
and, for authenticated user, identifiers of user's reviews (including not yet moderated ones):

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 15,
      "comment": "Very nice and handy",
      "rating": {"value": 5, "text": "Excellent"},
      "weight": 1,
      "submit_date": "2026-11-09T12:00:00Z",
      "is_public": true,
      "user": {"id": 3, "name": "john"},
      "site": 1
    },
    ...
  ],
  "statistics": {
    "value": 4.333333333333333,
    "text": "Very Good",
    "ratings": [{"rating": 4, "count": 2}, {"rating": 5, "count": 1}]
  },
  "user_reviews": [15]
}
```

To post a review, get the form first and send back values of its hidden security fields (```content_type```,
```object_pk```, ```timestamp```, ```security_hash```) together with ```rating``` and ```comment```. The data is
validated exactly as the HTML form: security hash expires in ```REVIEW_COMPOSE_TIMEOUT``` and spam protection is
applied. Modifying a review requires the same data.

See [REST API documentation](https://django-rated-reviews.readthedocs.io/en/stable/api.html) for details and examples.

## Customization

All configuration settings are optional.

#### REVIEW_MAX_LENGTH

The maximum length of the review comment field, in characters. Comments longer than this will be rejected. Defaults to ```3000```.

#### REVIEW_PUBLISH_UNMODERATED

If ```False``` (default) reviews are not published until they are moderated in admin. If user modifies existing review it is considered unmoderated again.

#### REVIEW_COMPOSE_TIMEOUT

The maximum review form timeout in seconds. The default value is ```2 * 60 * 60``` (2 hours).

#### REVIEW_RATING_CHOICES

Custom rating choices, each represented by one star (currently the maximum supported number is 10). Default choices are:

```python
REVIEW_RATING_CHOICES = (
    ('1', _('Terrible')),
    ('2', _('Poor')),
    ('3', _('Average')),
    ('4', _('Very Good')),
    ('5', _('Excellent')),
)
```

#### REVIEW_SHOW_RATING_TEXT

If ```True``` (default) rating text (as specified by choices) is displayed next to rating stars. 

#### REVIEW_ALLOW_PROFANITIES

If ```False``` review comment is checked against words in ```PROFANITIES_LIST```. If it contains any of the words, review is rejected.

#### REVIEW_ADMIN_LINK_SYMBOL

Review admin exposes a link to review on a web site. By default it is shown as &#9654;. It can be changed to any other symbol or text,
e.g. if Font Awesome is attached to admin the following setting can be used: ```'<i class="fas fa-external-link-alt"></i>'```.

#### REVIEW_APP

Name of a custom reviews app (it must be in ```INSTALLED_APPS```). The app can define any of the following functions
in its ```__init__.py```, the default implementation is used for functions that are not defined:

| Function                              | Returns                                                     | Default                                                |
|---------------------------------------|-------------------------------------------------------------|--------------------------------------------------------|
| `get_review_model()`                  | Review model, a subclass of `UserReviewAbstractModel`       | `reviews.models.Review`                                |
| `get_review_form()`                   | Review form class                                           | `reviews.forms.ReviewForm`                             |
| `get_review_form_target()`            | URL that review form is posted to                           | URL of `post-review` view                              |
| `get_review_user_weight(user, target)`| Rating weight of a review by `user` for `target` object     | `1`                                                    |
| `get_review_site_id(request)`         | Site ID that reviews are posted to and listed for           | `SITE_ID` setting or site of the request               |
| `get_review_rating_text(rating)`      | Text for a rating, which can be fractional (average rating) | Text from `REVIEW_RATING_CHOICES` for rounded rating   |
| `get_review_api_user_serializer()`    | REST API serializer class for review author                 | Serializer with user `id` and `name` (`str(user)`)     |
| `get_review_api_pagination_class()`   | REST API pagination class for review lists                  | `reviews.api.ReviewPagination` (20 reviews per page)   |

### Examples

#### Custom rating weight definition

```python
def get_review_user_weight(user, target):
    if user.has_perm('reviews.can_moderate'):
        return 50
    from .models import Product, Order
    if isinstance(target, Product):
        count = Order.objects.filter(user=user.pk,
                                     item__product=target.pk,
                                     status=Order.STATUS_DONE
                                     ).count()
        if count > 0:
            return 10
    return 1
```

#### Site detected by custom middleware

```python
def get_review_site_id(request):
    return request.site.id
```

#### Custom REST API representation of review author and pagination

```python
def get_review_api_user_serializer():
    from .serializers import UserListSerializer
    return UserListSerializer


def get_review_api_pagination_class():
    from .api import StandardResultsSetPagination
    return StandardResultsSetPagination
```

## Upgrading to 2.0

* Python 3.10+ and Django 5.2+ are required.
* Migration ```0003``` changes ```Review``` primary key to ```BigAutoField```. Reviews app does not depend on
  ```DEFAULT_AUTO_FIELD``` setting anymore. Run ```manage.py migrate``` after upgrade.
* The site of a review posted with HTML form is determined by ```get_review_site_id()``` (with the same default
  behaviour), so that HTML form, template tags and REST API are consistent.

## Development

Tests are run with [tox](https://tox.wiki/) against all supported Python and Django versions, with and without
Django REST framework:

```shell
pip install tox
tox                             # all available Python versions and documentation
tox -e py313-django61-drf       # particular environment
tox -e docs                     # check that documentation builds without warnings
python tests/runtests.py        # current virtual environment
```

Documentation sources are in ```docs``` directory, they are built with [Sphinx](https://www.sphinx-doc.org/)
and published on [Read the Docs](https://django-rated-reviews.readthedocs.io/).

To release a new version, update ```version``` in ```pyproject.toml```, commit the change and push a tag
with the same version:

```shell
git tag v2.0.0
git push origin v2.0.0
```

GitHub workflow runs the tests, publishes the package to TestPyPI and PyPI, creates GitHub release and builds
documentation of the release on Read the Docs.

## Credits

Application code is derived from [Django “excontrib” Comments](https://github.com/django/django-contrib-comments/).

Rating widget uses [star-rating.js library](https://github.com/pryley/star-rating.js) by Paul Ryley.
