import os
import sys
from my_package.classes.rman_api import RmanApiExtended

def pop_arg(name, array):
    result = None
    try:
        n = array.index(name)
        result = array.pop(n+1)
        array.pop(n)
    except:
        pass

    return result

def collect_kwargs(array):
    result = {}
    for item in array:
        if "--KWARG_" in item:
            name = item.replace("--KWARG_")
            value = pop_arg(item,array)
            result[name] = value

    return result

if __name__ == '__main__':
    print('RMAN API version 0.1. INIT.')
    parse = sys.argv

    kwargs = collect_kwargs(parse)

    url = pop_arg('--slack-url',parse)
    logs = pop_arg('--log-to-file',parse)
    debug = pop_arg('--debug',parse)

    print('RMAN API: Create task.')
    exe_location = os.sep.join(parse.pop(0).split(os.sep)[:-1])
    action = parse.pop(0)

    cls = RmanApiExtended(parse=parse,logs=logs,url=url,debug=debug,work_dir=exe_location)
    cls.run(action,**kwargs)

    print('RMAN API: Send logs.')
    cls.close()

    print('RMAN API: End.')

