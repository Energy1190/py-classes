import os

# Function, to initialize Flask applications.
def main(app,*args,**kwargs):
    # Easy start.
    if not len(args) and not len(kwargs):
        return app.run(host="0.0.0.0", port=5000, threaded=True)

    host = str(kwargs.get('host') or "0.0.0.0")
    port = int(kwargs.get('port') or 5000)
    threaded = bool(kwargs.get('threaded') or True)

    if kwargs.get('db_save_file'):
        os.environ['DB_FILE'] = kwargs.get('db_save_file')

    if kwargs.get('db_dir_path'):
        os.environ['DB_PATH'] = kwargs.get('db_dir_path')

    return app.run(host=host, port=port, threaded=threaded)
