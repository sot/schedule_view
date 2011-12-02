# Set the task name
TASK = schedule_view

# set a version for the "make dist" option
VERSION = 0.1

# Uncomment the correct choice indicating either SKA or TST flight environment
FLIGHT_ENV = SKA


include /proj/sot/ska/include/Makefile.FLIGHT

DATA = task_schedule.cfg
SHARE = get_schedules.py TableParse.py 
TEMPLATES = templates/schedule.html templates/master_schedule.html

install:
ifdef TEMPLATES
	mkdir -p $(INSTALL_SHARE)/templates/
	rsync --times --cvs-exclude $(TEMPLATES) $(INSTALL_SHARE)/templates/
endif
ifdef SHARE
	mkdir -p $(INSTALL_SHARE)
	rsync --times --cvs-exclude $(SHARE) $(INSTALL_SHARE)/
endif
ifdef DATA
	mkdir -p $(INSTALL_DATA)
	rsync --times --cvs-exclude $(DATA) $(INSTALL_DATA)/
endif

