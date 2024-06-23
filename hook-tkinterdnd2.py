from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os

# Function to filter out osx and linux folders
def filter_platform_files(datas):
    filtered_datas = []
    for source, target in datas:
        if not any(platform in source for platform in ['osx', 'linux']):
            filtered_datas.append((source, target))
    return filtered_datas

# Collect data files and filter out unnecessary folders
datas = collect_data_files('tkinterdnd2')
datas = filter_platform_files(datas)

# Collect dynamic libraries and filter out unnecessary folders
binaries = collect_dynamic_libs('tkinterdnd2')
binaries = filter_platform_files(binaries)

# For CICD commit tags in our title
if os.path.exists('build_details.txt'):
    datas.append(('build_details.txt', '.'))
