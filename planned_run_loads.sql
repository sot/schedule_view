create view planned_run_loads as 
select load_segment_id, l.load_segment, l.year, l.load_scs,
p.replan, p.bcf_cmd_count, p.replan_cmds, 
p.processing_tstart, p.processing_tstop, 
b.file, b.sumfile_modtime, 
b.first_cmd_time, b.last_cmd_time, 
t.dir, t.datestart, t.datestop 
from timelines as t 
join load_segments l on t.load_segment_id = l.id 
join tl_built_loads b on 
(l.load_segment = b.load_segment 
and l.year = b.year 
and l.load_scs = b.load_scs) 
join tl_processing p on 
(b.sumfile_modtime = p.sumfile_modtime 
and b.file = p.file);

