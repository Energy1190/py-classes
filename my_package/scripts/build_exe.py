import os
import shutil
import my_package

def main():
    path = my_package.__file__.split(os.sep)[:-1]

    path_to_folder = os.sep.join(path + ['src_exe'])
    path_to_dist = os.path.join(os.getcwd(), 'dist')
    path_to_build = os.path.join(os.getcwd(), 'build')

    template = 'pyinstaller --clean --onefile --distpath {} --workpath {} {}'
    for item in os.listdir(os.path.join(path_to_folder)):
        if item == '__init__.py':
            continue

        if len(item.split('.')) and item.split('.')[-1] == 'py':
            file = os.path.join(path_to_folder, item)
            print('BUILD: {}'.format(item))

            os.system(template.format(path_to_dist,path_to_build,file))
            shutil.rmtree(path_to_build)
            print('DONE: {}'.format(item))

    for item in os.getcwd():
        path = os.path.join(os.getcwd(), item)
        if os.path.isfile(path) and len(path.split('.')) and path.split('.')[-1] == 'spec':

            print('REMOVE: {}'.format(path))
            os.remove(path)

if __name__ == '__main__':
    main()