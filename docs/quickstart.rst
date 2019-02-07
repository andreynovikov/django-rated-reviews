=================
Quick start guide
=================

To get started using the ``reviews`` app, follow these steps:

#. Install the reviews app by running ``pip install django-rated-reviews``.

#. `Enable the "sites" framework <enabling-the-sites-framework>`_ by adding
   ``'django.contrib.sites'`` to ``INSTALLED_APPS`` and defining ``SITE_ID``.

#. Install the reviews framework by adding ``'reviews'`` to ``INSTALLED_APPS``.

#. Run ``manage.py migrate`` so that Django will create the review tables.

#. Add the reviews app's URLs to your project's ``urls.py``:

   .. code-block:: python

        urlpatterns = [
            ...
            url(r'^reviews/', include('reviews.urls')),
            ...
        ]

#. Use the `review template tags`_ below to embed reviews in your templates.

You might also want to examine :ref:`the available settings <settings-reviews>`.


Review template tags
=====================

You'll primarily interact with the reviews system through a series of template
tags that let you embed reviews and generate forms for your users to post them.

Like all custom template tag libraries, you'll need to load tags before you can
use them::

    {% load reviews %}

Once loaded you can use the template tags below.

Specifying which object reviews are attached to
------------------------------------------------

All reviews are "attached" to some parent object. This can be any
instance of a Django model. Each of the tags below gives you a couple of
different ways you can specify which object to attach to:

#. Refer to the object directly -- the most common method. Most of the
   time, you'll have some object in the template's context you want
   to attach the review to; you can simply use that object.

   For example, in a article page that has a variable named ``article``,
   you could use the following to load the number of reviews::

        {% get_review_count for article as review_count %}.

#. Refer to the object by content-type and object id. You'd use this method
   if you, for some reason, don't actually have direct access to the object.

   Following the above example, if you knew the object ID was ``14`` but
   didn't have access to the actual object, you could do something like::

        {% get_review_count for blog.article 14 as review_count %}

   In the above, ``blog.article`` is the app label and (lower-cased) model
   name of the model class.

Displaying reviews
-------------------

To display a list of reviews, you can use the template tags ``render_review_list``
or ``get_review_list``.

Quickly rendering a review list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to display a list of reviews for some object is by using
``render_review_list``::

    {% render_review_list for [object] %}

For example::

    {% render_review_list for product %}

This will render reviews using a template named ``reviews/list.html``.

Rendering a custom review list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To get the list of reviews for some object, use ``get_review_list``::

    {% get_review_list for [object] as [varname] %}

For example::

    {% get_review_list for product as review_list %}
    {% for review in review_list %}
        ...
    {% endfor %}

This returns a list of :class:`~reviews.models.Review` objects;
see :doc:`the review model documentation <models>` for
details.

Linking to reviews
-------------------

To provide a permalink to a specific review, use ``get_review_permalink``::

    {% get_review_permalink review_obj [format_string] %}

By default, the named anchor that will be appended to the URL will be the letter
'r' followed by the review id, for example 'r82'. You may specify a custom
format string if you wish to override this behavior::

    {% get_review_permalink review "#review%(id)s-with-%(rating)s"%}

The format string is a standard python format string. Valid mapping keys
include any attributes of the review object.

Regardless of whether you specify a custom anchor pattern, you must supply a
matching named anchor at a suitable place in your template.

For example::

    {% for review in review_list %}
        <a name="r{{ review.id }}"></a>
        <a href="{% get_review_permalink review %}">
            permalink for review #{{ forloop.counter }}
        </a>
        ...
    {% endfor %}

Counting reviews
-----------------

To count reviews attached to an object, use ``get_review_count``::

    {% get_review_count for [object] as [varname]  %}

For example::

        {% get_review_count for product as review_count %}

        <p>This product has {{ review_count }} reviews.</p>


Displaying the review post form
--------------------------------

To show the form that users will use to post a review, you can use
``render_review_form`` or ``get_review_form``

Quickly rendering the review form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to display a review form is by using
``render_review_form``::

    {% render_review_form for [object] %}

For example::

    {% render_review_form for product %}

This will render a form using a template named ``reviews/form.html``.

Rendering a custom review form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want more control over the look and feel of the review form, you may use
``get_review_form`` to get a ``form object <django.forms.Form>`` that
you can use in the template::

    {% get_review_form for [object] as [varname] %}

A complete form might look like::

    {% get_review_form for product as form %}
    <table>
      <form action="{% review_form_target %}" method="post">
        {% csrf_token %}
        {{ form }}
        <tr>
          <td colspan="2">
            <input type="submit" name="submit" value="Post">
          </td>
        </tr>
      </form>
    </table>

Be sure to read the `notes on the review form`_, below, for some special
considerations you'll need to make if you're using this approach.

Getting the review form target
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may have noticed that the above example uses another template tag --
``review_form_target`` -- to actually get the ``action`` attribute of the
form. This will always return the correct URL that reviews should be posted to;
you'll always want to use it like above::

    <form action="{% review_form_target %}" method="post">

Redirecting after the review post
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify the URL you want to redirect to after the review has been posted,
you can include a hidden form input called ``next`` in your review form. For example::

    <input type="hidden" name="next" value="{% url 'review_was_posted' %}" />

.. _notes-on-the-review-form:

Notes on the review form
-------------------------

The form used by the review system has a few important anti-spam attributes you
should know about:

* It contains a number of hidden fields that contain timestamps, information
  about the object the review should be attached to, and a "security hash"
  used to validate this information. If someone tampers with this data --
  something spammers will try -- the review submission will fail.

  If you're rendering a custom review form, you'll need to make sure to
  pass these values through unchanged.

* The timestamp is used to ensure that "reply attacks" can't continue very
  long. Users who wait too long between requesting the form and posting a
  review will have their submissions refused.

* The review form includes a "honeypot_" field. It's a trap: if any data is
  entered in that field, the review will be considered spam (spammers often
  automatically fill in all fields in an attempt to make valid submissions).

  The default form hides this field with a piece of CSS and further labels
  it with a warning field; if you use the review form with a custom
  template you should be sure to do the same.

The reviews app also depends on the more general `Cross Site Request
Forgery protection`_ that comes with Django.  As described in
the documentation, it is best to use ``CsrfViewMiddleware``.  However, if you
are not using that, you will need to use the ``csrf_protect`` decorator on any
views that include the review form, in order for those views to be able to
output the CSRF token and cookie.

.. _enabling-the-sites-framework: https://docs.djangoproject.com/en/stable/ref/contrib/sites/#enabling-the-sites-framework
.. _cross site request forgery protection: https://docs.djangoproject.com/en/stable/ref/csrf/
.. _honeypot: http://en.wikipedia.org/wiki/Honeypot_(computing)
