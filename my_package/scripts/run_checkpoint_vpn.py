import sys
import time
import argparse
from traceback import format_exc
from my_package.classes.check_point_vpn import SeleniumBase, SeleniumExtended
from my_package.scripts.send_slack_notification import main as notification
def stop(obj):
    try: obj.stop()
    except: pass

def create_obj(obj,args,options):
    kwargs = {}
    kwargs['options'] = options
    class_type = SeleniumBase
    if args.auth_window_title:
        kwargs['auth_window_title'] = args.auth_window_title
        class_type = SeleniumExtended
    if args.auth_button_title:
        kwargs['auth_button_title'] = args.auth_button_title
        class_type = SeleniumExtended
    if args.slack_url:
        kwargs['notifications'] = args.slack_url
        class_type = SeleniumExtended
    
    obj = class_type(args.site, **kwargs)
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
            if args.slack_url: notification(args.slack_url, 'Error in CheckPointVPN.', traceback=format_exc())
            obj = create_obj(obj, args, options)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('site', help='Website address. For example: http://example.com')
    parser.add_argument('--auth_window_title', help='The title of the window with the offer of a certificate')
    parser.add_argument('--auth_button_title', help='The inscription on the buttons with confirmation, usually - OK')
    parser.add_argument('--slack_url')

    args = parser.parse_args()
    if not args.site:
        print('You did not enter the required argument - website address.')
        sys.exit(1)

    main_cycle(args)

if __name__ == '__main__':
    main()