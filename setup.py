import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='django-rated-reviews',
    version='1.0.1',
    license='MIT',
    author='Andrey Novikov',
    author_email='novikov@gmail.com',
    description='Rated reviews for Django',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/andreynovikov/django-rated-reviews/tree/master',
    project_urls={
        'Documentation': 'https://django-rated-reviews.readthedocs.io/',
        'Source': 'https://github.com/andreynovikov/django-rated-reviews/',
        'Tracker': 'https://github.com/andreynovikov/django-rated-reviews/issues',
    },
    packages=setuptools.find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 6 - Mature',
        'Framework :: Django',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=['Django>=1.11'],
    test_suite='tests.runtests.main'
)
