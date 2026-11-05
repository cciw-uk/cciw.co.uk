# Used by run_benchmark.py experiments (via PYTHONPATH) to test the effect of
# restoring the pre-3.14 default multiprocessing start method ("fork") on Linux.
import multiprocessing

multiprocessing.set_start_method("fork")
