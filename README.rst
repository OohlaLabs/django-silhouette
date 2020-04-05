=================
Django Silhouette
=================

.. image:: https://travis-ci.org/jthi3rry/django-silhouette.svg?branch=master
    :target: https://travis-ci.org/jthi3rry/django-silhouette

.. image:: https://coveralls.io/repos/jthi3rry/django-silhouette/badge.png?branch=master
    :target: https://coveralls.io/r/jthi3rry/django-silhouette

Silhouette is a form templating app for Django just like `Django Crispy Forms <https://github.com/maraujop/django-crispy-forms>`_
or `Django Floppy Forms <https://github.com/gregmuellegger/django-floppyforms>`_.
Unlike these, form templating with Silhouette is exclusively done at the template level. Your form classes don't need to change.

You no longer have to plague your forms with widgets that are only here to add some css or form helpers simulating html. Your django forms are
used for server-side input validation, your templates are the only ones responsible for making them look awesome.

If you happen to have a team of frontend developers who don't want to dig deep into the darkness of your
python code to change a class on one of your field's help text, they'll probably thank you.
And even if you don't, you'll probably be happy to keep your form templating code where it belongs: in your templates.

Silhouette also lets you create global themes and form specific themes to style everything from the form tag down to field errors and widget types.
Since everything happens in templates, you can use template inheritance and blocks to achieve anything you like. Read on.

Installation
============

::

    pip install django-silhouette


In your settings.py

::

    INSTALLED_APPS = [
        ...
        "silhouette",
        ...
    ]


Getting Started
===============

Instead of explaining the internals of Silhouette head-on, let's get a feel for it by creating a form styled with Twitter's Bootstrap.
We'll assume that your layout already includes the bootstrap stylesheet.

Let's pretend we have an imaginary form like `this one <http://getbootstrap.com/css/#forms>`_::

    class BasicForm(forms.Form):

        email_address = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)
        file = forms.FileField()
        check_me_out = forms.BooleanField()

With Silhouette, you could display the form like this (in the imaginary template ``templates/app/index.html``)::

    {% load silhouette_tags %}

    <form>
        {% csrf_token %}
        <div class="form-group{% if form.name.errors %} has-error{% endif %}">
            {% field form.name widget_placeholder="Enter email" widget_id="exampleInputEmail1" widget_class="form-control" %}
        </div>
        <div class="form-group{% if form.password.errors %} has-error{% endif %}">
            {% field form.password widget_placeholder="Password" widget_id="exampleInputPassword1" widget_class="form-control" %}
        </div>
        <div class="form-group{% if form.file.errors %} has-error{% endif %}">
            {% field form.file help_text_contents="Example block-level help text here." help_text_class="help-block" %}
        </div>
        <div class="checkbox{% if form.check_me_out.errors %} has-error{% endif %}">
            <label>{% form_widget form.check_me_out %} {{ form.check_me_out.label }}</label>
        </div>
        <button type="submit" class="btn btn-default">Submit</button>
    </form>

This will give you the form as per Bootstrap's example. We didn't do anything about errors, but Silhouette will
also render these for free (you could add ``errors_class="alert alert-danger"`` to each field to display errors using bootstrap's alerts).

This is still not ideal though. All our forms should be displayed consistently and there will be a lot of repetition if we need to do this for
every single form.

Let's create a global theme that will handle all this for us.

Global Themes
=============

In your ``settings.py``, configure the silhouette theme name. By default this is::

    SILHOUETTE_THEME = "default"

Let's change the theme name to ``bootstrap``::

    SILHOUETTE_THEME = "bootstrap"

Create a file ``templates/silhouette/bootstrap/fields/field.html``. You could create a template from scratch and render the label,
widget, errors and help text individually (refer to the `base field template <https://github.com/OohlaLabs/django-silhouette/blob/master/silhouette/templates/silhouette/base/fields/field.html>`_ for an example),
but let's see how to take advantage of Django's template inheritance and Silhouette's base theme

::

    {% extends "silhouette/base/fields/field.html" %}

    {% load silhouette_tags silhouette_filters %}

    {% block field %}
        <!-- Output field wrapper based on widget type -->
        {% if field|is_checkbox_input %}
            <div class="checkbox{% if field.errors %} has-error{% endif %}">
                {{ block.super }}
            </div>
        {% else %}
            <div class="form-group{% if field.errors %} has-error{% endif %}">
                {{ block.super }}
            </div>
        {% endif %}
    {% endblock %}

    {% block widget %}
        <!-- Output field widget based on its type -->
        {% if field|is_file_input or field|is_checkbox_input %}
            {% field_widget field %}
        {% else %}
            {% field_widget field class="form-control" %}
        {% endif %}
    {% endblock %}

    {% block help_text %}
        <!-- Output help text consistently -->
        {% field_help_text field class="help-block" %}
    {% endblock %}

    {% block errors %}
        <!-- Output errors consistently -->
        {% field_errors field class="alert alert-danger" %}
    {% endblock %}

Notice that the template's context has a ``field`` variable that refers to the form's bound field being rendered (your default context is also available).

Now we just need an extra template for checkboxes as we want to wrap the label around the field.

In ``templates/silhouette/bootstrap/fields/checkbox_input_field.html``, extend your own field template with::

        {% extends "silhouette/bootstrap/fields/field.html" %}

        {% load silhouette_tags %}

        {% block label %}
            <!-- Do not render the label here -->
        {% endblock %}

        {% block widget %}
            <label>{% field_widget field %} {{ field.label }}</label>
        {% endblock %}

Notice that the template name for a checkbox field is the widget's class name in underscore notation ``checkbox_input`` followed by the ``_field`` suffix.

Your ``templates/app/index.html`` template now can become::

    {% load silhouette_tags %}

    <form>
        {% csrf_token %}
        {% field form.name widget_placeholder="Enter email" widget_id="exampleInputEmail1" %}
        {% field form.password widget_placeholder="Password" widget_id="exampleInputPassword1" %}
        {% field form.file help_text_contents="Example block-level help text here." %}
        {% field form.check_me_out %}
        <button type="submit" class="btn btn-default">Submit</button>
    </form>

And all your future forms will use the bootstrap theme.

If you need a specific class added to any of the fields, Silhouette will merge these for you with the ones defined in a theme::

    {% field form.password ... widget_class="extra-class" %}

Will output::

    <div class="form-group">
        ...
        <input type="password" ... class="form-control extra-class" />
        ...
    </div>

Now you can extend your theme by adding new widgets like radio buttons, select boxes and so on.

Form Themes
===========

Field templates and global themes remove a lot of the complexity usually involved with displaying forms with Django. But Silhouette
doesn't stop here and also allows you to create form specific theme.

For example, let's change our ``templates/app/index.html`` template, and use the second bootstrap example using the ``form-inline`` class.

We'll also introduce the `silhouette` tag that allows you to display forms in a single line of code::

    {% load silouhette_tags %}

    {% silhouette form method="post" action="/action" class="form-inline" errors_class="alert alert-warning" %}

This will render::

    <form enctype="multipart/form-data" class="form-inline" method="post" action="/action" >
        <input type="hidden" name="csrf_token" value="...." />

        <!-- Errors will show up here if any -->
        <ul class="alert alert-warning">
            <li>....</li>
        </ul>

        <!-- Fields will show up here -->
        <div class="form-group">
            ...
        </div>
        ...

        <!-- Controls will show up here -->
        <button type="submit">Submit</button>

        <!-- Media will show up here if any -->
        <script ...></script>

    </form>

However, by doing so, we just lost the specific attributes that were passed to each field like placehoders, ids, etc.
as well as our styled submit button.

Our fields and button are specific to our form, so let's create a "form theme" for these.

In ``templates/silhouette/basic_form/fields.html``::

    {% extends "silhouette/base/forms/fields.html" %}

    {% load silhouette_tags %}

    {% block visible_fields %}
        {% field form.name widget_placeholder="Enter email" widget_id="exampleInputEmail1" %}
        {% field form.password widget_placeholder="Password" widget_id="exampleInputPassword1" %}
        {% field form.file help_text_contents="Example block-level help text here." %}
        {% field form.check_me_out %}
    {% endblock %}

Note that the template is not created under the ``bootstrap`` theme, but under the ``basic_form`` "theme". This is the form's class name ``BasicForm`` in underscore notation.

Now, in ``templates/silhouette/basic_form/controls.html``::

    <button type="submit" class="btn btn-default">Submit</button>

Note that you could override this in the global theme by modifying ``templates/silhouette/bootstrap/forms/controls.html`` instead.

Just like with the global theme, you can override any field, label, widget, field errors, help text in your form by
creating a template in ``templates/silhouette/basic_form/fields/{{overridden_part}}.html``.

Anything usually possible with Django templates is possible with Silhouette.
Silhouette provides a base theme with what we assumed could be useful and generic, but you can ignore it or replace it altogether.

Template Loader
===============

When rendering a template for a field, form or formset, Silhouette tries and find the first template that exists using a list of path patterns.

The general idea is that Silhouette will look for a template from the most specific to the most generic place.

For example, when doing ``{% field form.field %}``, Silhouette will check:

* if a template exists for the field in the form's theme
* if one exists for the field's widget in the form's theme
* if one exists for the field's widget in the global theme
* if one exists for all fields in the form's theme
* if one exists for all fields in the global theme
* otherwise, it will fallback to using the base field template shipped with Silhouette

These rules are defined like this in the ``SILHOUETTE_PATTERNS`` setting:

* ``{path}/{form}/fields/{field}.html``
* ``{path}/{form}/fields/{widget}_field.html``
* ``{path}/{theme}/fields/{widget}_field.html``
* ``{path}/{form}/fields/field.html``
* ``{path}/{theme}/fields/field.html``
* ``silhouette/base/fields/field.html``

Where ``{path}`` is the value of the ``SILHOUETTE_PATH`` setting, ``{theme}`` is the value of the ``SILHOUETTE_THEME`` setting, ``{form}`` is the form class
name in underscore notation, ``{field}`` is the field name in your form, and ``{widget}`` is the widget class name in underscore notation.

Each tag has its own lookup list of patterns. See the `default settings <https://github.com/OohlaLabs/django-silhouette/blob/master/silhouette/settings.py>`_
for a full list. For advanced usage or if you simply don't like the convention and want to use another one, new patterns can be added or the lookup order modified by changing the ``SILHOUETTE_PATTERNS`` setting.

Bypassing the Template Lookup
-----------------------------

Tags also accept a template argument to render a specific template. For example::

    {% field form.field1 template="path/to/field1.html" %}

When using the template argument, field patterns will be ignored.

Overriding Path and Theme
-------------------------

Path and theme can also be overridden for a given tag. For example::

    {% field form.field1 path="form-themes" theme="my-theme" %}

When using these arguments, the value of `{path}` and `{theme}` are overridden for the given tag, and all tags used within its context.
So in the above example, the widget, label, help_text and errors rendered by `field` would use the path `form-themes` and the theme `my-theme`.

Running Tests
=============

Get a copy of the repository::

    git clone git@github.com:OohlaLabs/django-silhouette.git .

Install `tox <https://pypi.python.org/pypi/tox>`_::

    pip install tox

Run the tests::

    tox

Contributions
=============

All contributions and comments are welcome.

Change Log
==========

v0.0.2
------
* Distribution description & homepage

v0.0.1
------
* Initial release
