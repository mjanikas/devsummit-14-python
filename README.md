devsummit-14-python
===================

Workflow to manage ArcGIS Online Content using Python.  Example focuses on the effects of Drought on the Wine Industry in the US.

An application that utilizes the logic given by https://github.com/arcpy/update-hosted-feature-service .

Special Instructions
--------------------

Edit the 'publish_service.py' file and add your Username/Password
Information.  Search for USERNAMEHERE and PASSWORDHERE to locate where the
information is necessary.  

You must also change your 'working_dir' variable within the
'drought_analysis' function.

The python script does not contain the automation portion of the workflow
to avoid unnecessary/unwanted calls to ArcGIS Online.  You may use the
core **os**, **sys** and **subprocess** modules to create cron jobs or you can choose
the quick and easy method: the **python-crontab** module.  Just *easy_install*
or *pip* it and then follow the simple instructions at: http://www.adminschoice.com/crontab-quick-reference/ .

