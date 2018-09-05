import sys
import time
import argparse
from my_package.classes.check_point_vpn import SeleniumBase, SeleniumExtended

def stop(obj):
    try: obj.stop()
    except: pass

def create_obj(obj,args,options):
    if not args.auth_window_title or not args.auth_button_title:
        obj = SeleniumBase(args.site, options=options)
    else:
        obj = SeleniumExtended(args.site, options=options,
                               auth_window_title=args.auth_window_title,
                               auth_button_title=args.auth_button_title)
    return obj

def main_cycle(args):
    obj = None
    options = {'ignoreProtectedModeSettings': True,
               'acceptSslCerts': True}

    while True:
        try:
            obj = create_obj(obj,args,options)
            obj.run()
            break
        except:
            time.sleep(5)
            if obj: stop(obj)
            obj = create_obj(obj, args, options)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('site', help='Website address. For example: http://example.com')
    parser.add_argument('--auth_window_title', help='The title of the window with the offer of a certificate')
    parser.add_argument('--auth_button_title', help='The inscription on the buttons with confirmation, usually - OK')

    args = parser.parse_args()
    if not args.site:
        print('You did not enter the required argument - website address.')
        sys.exit(1)

    main_cycle(args)

if __name__ == '__main__':
    main()