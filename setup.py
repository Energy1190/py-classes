from setuptools import setup, find_packages

setup(name='my_package',
      version='0.17.3',
      description='A set of my classes, functions, projects and web interfaces.',
      url='https://github.com/Energy1190/py-projects',
      author='Energy1190',
      author_email='energyneo0@gmail.com',
      packages=find_packages(),
      install_requires=[
          'jinja2',
          'ldap3>=2.1.0',
          'selenium',
          'flask',
          'paramiko',
          'requests',
		  'cx_Oracle'
      ],
      include_package_data=True,
      zip_safe=False)
