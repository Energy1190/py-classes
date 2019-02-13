import os
import sys

# Function, to initialize Flask applications.
def main(app,*args,**kwargs):
    # Easy start.
    if not len(args) and not len(kwargs):
        return app.run(host="0.0.0.0", port=5000, threaded=True)

    host = str(kwargs.get('host') or "0.0.0.0")
    port = int(kwargs.get('port') or 5000)
    threaded = bool(kwargs.get('threaded') or True)

    if not hasattr(app, 'local_vars'):
        app.local_vars = {}

    if kwargs.get('db_save_file'):
        app.local_vars['DB_FILE'] = kwargs.get('db_save_file')

    if kwargs.get('db_dir_path'):
        app.local_vars['DB_PATH'] = kwargs.get('db_dir_path')

    if kwargs.get('work_dir_path'):
        pid = os.getpid()
        name = kwargs.get('name') or 'unknow_proc'
        pid_file = os.path.join(kwargs.get('work_dir_path'), '{}_{}.pid'.format(str(pid),name))
        if os.path.exists(pid_file):
            print('REMOVE .PID BEFORE RUN.')
            return

        log_file_stdout = os.path.join(kwargs.get('work_dir_path'), '{}_{}_stdout.log'.format(str(pid),name))
        log_file_stderr = os.path.join(kwargs.get('work_dir_path'), '{}_{}_stderr.log'.format(str(pid),name))

        sys.stdout = open(log_file_stdout, 'w')
        sys.stderr = open(log_file_stderr, 'w')

    return app.run(host=host, port=port, threaded=threaded)
