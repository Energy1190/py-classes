import sys
import argparse
from my_package.classes.check_point_vpn import SeleniumBase, SeleniumExtended

def main():
    options = {'ignoreProtectedModeSettings': True,
               'acceptSslCerts': True}

    parser = argparse.ArgumentParser()

    parser.add_argument('site', help='Website address. For example: http://example.com')
    parser.add_argument('--auth_window_title', help='The title of the window with the offer of a certificate')
    parser.add_argument('--auth_button_title', help='The inscription on the buttons with confirmation, usually - OK')

    args = parser.parse_args()
    if not args.site:
        print('You did not enter the required argument - website address.')
        sys.exit(1)

    if not args.auth_window_title or not args.auth_button_title:
        obj = SeleniumBase(args.site,options=options)
    else:
        obj = SeleniumExtended(args.site,options=options,
                                         auth_window_title=args.auth_window_title,
                                         auth_button_title=args.auth_button_title)

    obj.run()
	
if __name__ == '__main__':
    main()