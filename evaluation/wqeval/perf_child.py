"""Isolated resource measurement for one native runner study."""
import resource
import sys
import time
from memorylab.runner import run
from .common import read,write
study=read(sys.argv[1]);out=sys.argv[2]
start=time.perf_counter();cold=run(study,out);cold_s=time.perf_counter()-start
start=time.perf_counter();warm=run(study,out);warm_s=time.perf_counter()-start
parent=resource.getrusage(resource.RUSAGE_SELF);child=resource.getrusage(resource.RUSAGE_CHILDREN)
scale=1 if sys.platform=='darwin' else 1024
write(sys.argv[3],{'cold':cold,'warm':warm,'cold_s':cold_s,'warm_s':warm_s,
      'parent_peak_rss_bytes':parent.ru_maxrss*scale,'largest_terminated_child_peak_rss_bytes':child.ru_maxrss*scale,
      'child_cpu_s':child.ru_utime+child.ru_stime,
      'rss_scope':'Separate parent maximum and largest terminated child maximum; not aggregate concurrent process peak'})
