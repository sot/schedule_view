#!/usr/bin/env python

import re
from glob import glob
import os
import time
import numpy as np
import jinja2
#import Ska.Numpy
from Ska.DBI import DBI
import TableParse


sqlaca = DBI(dbi='sybase', server='sybase', user='aca_read', database='aca')

mp_sched_path = '/proj/web-icxc/htdocs/mp/schedules'
mp_mplogs_path = '/proj/web-icxc/htdocs/mp/mplogs'
file_nav = {'mplogs_url': 'file://%s' % mp_mplogs_path,
            'mp_sched_path': mp_sched_path,
            'mp_sched_url': 'file://%s' % mp_sched_path}
web_nav = {'mplogs_url': 'https://icxc.harvard.edu/mp/mplogs',
           'mp_sched_path': mp_sched_path,
           'mp_sched_url': 'https://icxc.harvard.edu/mp/schedules/'}


# this is only used if we can't determine the cycle from the path
cycle_table = {'13': ('2011:275:20:48:22', '2999:001:00:00:00'),
               '12': ('2010:263:00:47:10', '2011:275:20:48:22'),
               '11': ('2009:340:19:44:00', '2010:263:00:47:10'),
               '10': ('2008:328:16:45:00', '2009:340:19:44:00'),
                '9': ('2007:323:09:45:00', '2008:328:16:45:00'),
                '8': ('2006:330:21:42:35', '2007:323:09:45:00'),
                '7': ('2006:023:05:04:27', '2006:330:21:42:35'),
                '6': ('2005:027:10:08:32', '2006:023:05:04:27'),
                '5': ('2003:292:01:39:03', '2005:027:10:08:32'),
                '4': ('2002:328:23:25:23', '2003:292:01:39:03'),
                '3': ('2001:316:02:07:50', '2002:328:23:25:23')}


def get_options():
    from optparse import OptionParser
    parser = OptionParser()
    parser.set_defaults()
    parser.add_option("--fileurls",
                      action='store_true',
                      help="Use file:/// URLS instead of http:// URLS")
    parser.add_option("--outdir",
                      default=os.path.join(os.environ['SKA'],
                                           'www', 'ASPECT', 'schedules'),
                      help="Directory for output")
    opt, args = parser.parse_args()
    return opt, args


def main(opt):
    """
    Perform a bunch of queries and processing to build something like the
    SOT MP schedule page, only with automated info about which loads ran.
    """

    outdir = opt.outdir
    nav = web_nav
    if opt.fileurls:
        nav = file_nav

    # fetch all of the loads that ran
    loads = sqlaca.fetchall("""select * from planned_run_loads
                               order by datestart""")

    # get all of the short term schedules from MP
    short_term_top = glob('%s/cycle*/????????.html' % mp_sched_path)
    short_terms = []
    for st_path in short_term_top:
        st_match = re.search('cycle(\d+)\/(\w{3}\d{4}\w).html', st_path)
        short_terms.append((int(st_match.group(1)), st_match.group(2)))
    short_terms = np.rec.fromrecords(short_terms, names=['cycle', 'label'])

    # fetch all mp comments from their schedule pages
    schedule_files = []
    for cycle in range(3, max(short_terms['cycle'])):
        schedule_files.append('%s/schedules_ao%s.html'
                              % ('/proj/web-icxc/htdocs/mp/html', cycle))
    schedule_files.append('/proj/web-icxc/htdocs/mp/html/schedules.html')

    comments = []
    for sched in schedule_files:
        sot_page = open(sched).read()
        table = TableParse.parse(sot_page)
        table = [x for x in table if len(x) > 0]
        table = [x for x in table if table[1] != '']
        last_sched = ''
        for line in table:
            if line[0] == '':
                line[0] = last_sched
            if line[0] != last_sched:
                last_sched = line[0]
        sot_table = np.rec.fromrecords(table[1:], names=table[0])
        for comment_week in sot_table[sot_table['Comment'] != '']:
            comments.append([comment_week['Week'],
                             comment_week['Version'],
                             comment_week['Comment']])
    mp_comments = np.rec.fromrecords(comments,
                                     names=['week', 'version', 'comment'])

    # everything that was planned
    planning = sqlaca.fetchall("""select * from tl_processing
                        where processing_tstart > '2002:007:13:35:00.000'
                        order by sumfile_modtime""")

    sched_keys = ['sumfile_modtime', 'dir', 'doprint',
                  'color', 'runstopcolor',
                  'label', 'name',
                  'version', 'sortday', 'cycle', 'st_link',
                  'planned_start', 'planned_stop',
                  'actual_cmd_start', 'actual_cmd_stop',
                  'comment', 'mp_comment']

    def_sched = dict(
        sumfile_modtime=None,
        dir=None,
        doprint=None,
        color='grey',
        runstopcolor='black',
        label=None,
        name=None,
        version=None,
        sortday=None,
        cycle=None,
        st_link=None,
        planned_start=None,
        planned_stop=None,
        actual_cmd_start=None,
        actual_cmd_stop=None,
        comment='&nbsp;',
        mp_comment='&nbsp;')


    # for each planned week, figure out if it ran or not, and either way,
    # push a dictionary for it to the master list
    schedule = []
    for week in planning:
        sched = def_sched.copy()
        comments = []
        sched['sumfile_modtime'] = week['sumfile_modtime']
        sched['dir'] = week['dir']
        sched['planned_start'] = week['planning_tstart']
        sched['planned_stop'] = week['planning_tstop']
        if week['replan'] == 1:
            comments.append('replan/re-open')
        labelmatch = re.search('\/\d{4}\/(\w{3}\d{4})\/ofls(\w?)\/',
                               week['dir'])
        if not labelmatch:
            raise ValueError("could not parse %s" % week['dir'])
        sched['label'] = "%s%s" % (labelmatch.group(1),
                                   labelmatch.group(2).upper())
        sched['version'] = labelmatch.group(2).upper()
        sched['name'] = labelmatch.group(1)
        sched_time = time.strptime(sched['name'], '%b%d%y')
        sched['sortday'] = time.strftime('%Y%j', sched_time)

        mp_comment_match = mp_comments[
                (mp_comments['week'] == sched['name'])
                & (mp_comments['version'] == sched['version'])]
        if len(mp_comment_match):
            sched['mp_comment'] = mp_comment_match[0]['comment']
        if sched['label'] in short_terms['label']:
            st = short_terms[short_terms['label'] == sched['label']][0]
            sched['cycle'] = int(st['cycle'])
            cycle_path = os.path.join(mp_sched_path,
                                      'cycle%d' % sched['cycle'],
                                      '%s.html' % sched['label'])
            cycle_url = (nav['mp_sched_url']
                         + "/cycle%d/" % sched['cycle']
                         + "%s.html" % sched['label'])
            if os.path.exists(cycle_path):
                sched['st_link'] = cycle_url
        else:
            for x in cycle_table:
                if ((week['processing_tstart'] > cycle_table[x][0])
                    and (week['processing_tstart'] < cycle_table[x][1])):
                    sched['cycle'] = int(x)
                    break

        # if the week flew
        if week['dir'] in loads['dir']:
            match_loads = loads[loads['dir'] == week['dir']]
            match_loads = np.sort(match_loads, order='datestart')
            sched['actual_cmd_start'] = min(match_loads['datestart'])
            sched['actual_cmd_stop'] = max(match_loads['datestop'])
            sched['color'] = 'black'
            load = match_loads[0]
            all_week_loads = sqlaca.fetchall(
                """select * from tl_built_loads
                   where file = '%s'
                   and sumfile_modtime = %f
                   order by load_segment"""
                % (load['file'], load['sumfile_modtime']))
            # does the run stop time match the plan?
            last_run_cmd_time = max(match_loads['datestop'])
            last_planned_cmd_time = max(all_week_loads['last_cmd_time'])
            if load['datestart'] > '2011:335':
                science_loads = match_loads[[match_loads['load_scs'] > 130]]
                if len(science_loads):
                    science_cmd_stop = max(science_loads['datestop'])
                    if science_cmd_stop < last_run_cmd_time:
                        comments.append('observing-only int. at %s'
                                        % science_cmd_stop)
                        sched['runstopcolor'] = 'darkgreen'
            if not last_run_cmd_time == last_planned_cmd_time:
                comments.append('int. at %s' % match_loads[-1]['datestop'])
                sched['runstopcolor'] = 'darkred'

        if len(comments):
            sched['comment'] = ', '.join(comments)
        schedule.append([sched[x] for x in sched_keys])

    # make records
    schedule = np.rec.fromrecords(schedule, names=sched_keys)

    # hack to mark rows to print week name only once per week
    schedule = np.sort(schedule, order='sortday')
    schedule['doprint'][schedule['name'][1:] != schedule['name'][0:-1]] = True
    schedule['doprint'][-1] = True

    # sort reverse by day
    schedule = schedule[::-1]

    # make html
    TASK_TEMPLATES = os.path.join(os.environ['SKA'], 'share',
                                  'schedule_view', 'templates')
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TASK_TEMPLATES))

    # loop to make cycle-specific pages
    cycle_labels = []
    template = jinja_env.get_template('schedule.html')
    for cycle in np.unique(schedule['cycle']):
        page = template.render(nav=nav,
                               schedule=schedule[schedule['cycle'] == cycle])
        f = open(os.path.join(outdir, 'schedule_%s.html' % cycle), 'w')
        f.write(page)
        f.close()
        # some ugliness to get the 8 characters (YYYY:DOY) of the min and max
        dstart = min(schedule[schedule['cycle'] == cycle]['planned_start'])
        dstop = max(schedule[schedule['cycle'] == cycle]['planned_stop'])
        daymin = dstart[0:8]
        daymax = dstop[0:8]
        cycle_labels.append(dict(cycle=cycle,
                                start=daymin,
                                stop=daymax,
                                file='schedule_%s.html' % cycle))
    # then make one big page
    page = template.render(nav=nav,
                           schedule=schedule)
    f = open(os.path.join(outdir, 'schedules_all.html' % cycle), 'w')
    f.write(page)
    f.close()

    # and make the most recent one again as a top page
    template = jinja_env.get_template('master_schedule.html')
    maxcycle = np.max(schedule['cycle'])
    page = template.render(nav=nav,
                           schedule=schedule[schedule['cycle'] == maxcycle],
                           cycles=cycle_labels)
    f = open(os.path.join(outdir, 'schedule.html'), 'w')
    f.write(page)
    f.close()

if __name__ == '__main__':
    opt, args = get_options()
    main(opt)
