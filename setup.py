from setuptools import setup

setup(
    name='stoic',
    version='0.1',
    py_modules=['stoic'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        stoic=stoic:cli
    ''',
)


