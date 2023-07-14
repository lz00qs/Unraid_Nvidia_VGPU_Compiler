import os
import subprocess
import shutil
import re
import argparse
import json


# Parsing command line instructions

from argparse import RawTextHelpFormatter

toolDescription = """ This tool is used to compile NVIDIA driver for Unraid OS.
"""

parser = argparse.ArgumentParser(description=toolDescription, formatter_class=RawTextHelpFormatter)
parser.add_argument("--clean-build", action="store_true", help="执行 clean build")

  
# 解析命令行参数
args = parser.parse_args()

# 获取当前工作目录
path = subprocess.run(["pwd"], capture_output=True, text=True)
path = path.stdout.strip()
print("Working directory: " + path)


# 创建临时文件夹
if not os.path.exists(os.path.join(path, "temp")):
    os.mkdir(os.path.join(path, "temp"))
    print("temp directory created, it seems this is the first time you run this script, use --clean-build to force clean build")
    args.clean_build = True
elif args.clean_build:
    print("clean build enabled")
    print("temp directory already exists, deleting...")
    shutil.rmtree(os.path.join(path, "temp"))
    os.mkdir(os.path.join(path, "temp"))
    print("temp directory created")
else:
    print("clean build disabled, will use existing temp directory")
    print("temp directory already exists, skipping...")

temp_path = os.path.join(path, "temp")

if args.clean_build is False:
    cmd = "rm -rf " + os.path.join(temp_path, "nvidia")
    if os.system(cmd) != 0:
        exit()

    cmd = "rm -rf " + os.path.join(temp_path, "output")
    if os.system(cmd) != 0:
        exit()


file_names = os.listdir(path)
nvd_file_name = ""
unraid_kernel_mods_name = ""


for file_name in file_names:
    if file_name.endswith(".run"):
        nvd_file_name = file_name
    elif "Unraid" in file_name:
        unraid_kernel_mods_name = file_name

nvd_file_path = os.path.join(path, nvd_file_name)
unraid_kernel_mods_path = os.path.join(path, unraid_kernel_mods_name)

print("NVIDIA driver file: " + nvd_file_path)
print("Unraid kernel mods file: " + unraid_kernel_mods_path)

  

if unraid_kernel_mods_name == "" or nvd_file_name == "":
    print("No NVIDIA driver file or Unraid kernel mods file found in current directory, exiting...")
    exit()

  

if args.clean_build:
    
    cmd = "unzip -q " + unraid_kernel_mods_path + " -d " + temp_path + "/" + os.path.splitext(unraid_kernel_mods_name)[0]
    if os.system(cmd) != 0:
        exit()

unraid_kernel_name = unraid_kernel_mods_name[:-4]

unraid_uname = ''

pattern = r"-\d+\.\d+\.\d+-\w+"

match = re.search(pattern, unraid_kernel_name)

if match:
    unraid_uname = match.group()[1:] # 去除开头的"-"

if unraid_uname == '':
    print("Unraid uname could not be found")
    exit()

print("Unraid uname: " + unraid_uname)

unraid_kernel_mods_extracted_path = os.path.join(temp_path, unraid_kernel_name)

print("Unraid kernel mods extracted to: " + unraid_kernel_mods_extracted_path)

  
  

# 使用正则表达式提取版本号

kernel_full_version = ""

kernel_major_version = ""

version_match = re.search(r"linux-(\d+\.\d+\.\d+)", unraid_kernel_mods_name)

if version_match:
    kernel_full_version = version_match.group(1)
    kernel_major_version = kernel_full_version.split(".")[0]

  

if kernel_full_version == "" or kernel_major_version == "":
    print("Failed to extract kernel version, exiting...")
    exit()

  

print("Kernel version: " + kernel_full_version)

  

if args.clean_build:
# 下载对应版本的内核源码
    # cmd = "wget -P " + temp_path + " https://www.kernel.org/pub/linux/kernel/v" + kernel_major_version + ".x/linux-" + kernel_full_version + ".tar.gz"
    cmd = ("cp " + os.path.join(path, "linux-" + kernel_full_version + ".tar.gz") + " " + temp_path)
    if os.system(cmd) != 0:
        exit()

# 解压内核源码
cmd = ("tar -C " + temp_path + " -xf " + os.path.join(temp_path, "linux-" + kernel_full_version + ".tar.gz"))
if os.system(cmd) != 0:
    exit()

kernel_src_path = os.path.join(temp_path, "linux-" + kernel_full_version)

print("Kernel source extracted to: " + kernel_src_path)

  

if args.clean_build:
# 复制编译配置文件
    cmd = ("cp -f " + os.path.join(unraid_kernel_mods_extracted_path, ".config") + " " + kernel_src_path)
    if os.system(cmd) != 0:
        exit()
    cmd = ("cp -rf " + os.path.join(unraid_kernel_mods_extracted_path, "*") + " " + kernel_src_path)
    if os.system(cmd) != 0:
        exit()
        
# if args.clean_build:
    file_names = os.listdir(kernel_src_path)
    patchs = []
    patch_src = []
    for file_name in file_names:
        if file_name.endswith(".patch"):
            patchs.append(file_name)
        # elif file_name.endswith(".c"):
        #     patch_src.append(file_name)
        # elif file_name.endswith(".h"):
        #     patch_src.append(file_name)
    print(str(len(patchs)) + " patchs found in kernel source directory")
    for patch in patchs:
        cmd = ("patch -p1 -d " + kernel_src_path + " < " + os.path.join(kernel_src_path, patch))
        if os.system(cmd) != 0:
            exit()
    # for src in patch_src:
    #     cmd = 
    cmd = ("cp " + unraid_kernel_mods_extracted_path + "/*.c" + " " + kernel_src_path + "/drivers/md/")
    if os.system(cmd) != 0:
            exit()
    cmd = ("cp " + unraid_kernel_mods_extracted_path + "/*.h" + " " + kernel_src_path + "/drivers/md/")
    if os.system(cmd) != 0:
            exit()

    # 进行一次编译保证编译环境正常
    cmd = "make -j$(nproc) -C " + kernel_src_path
    if os.system(cmd) != 0:
        exit()


cmd = "chmod +x " + nvd_file_path
if os.system(cmd) != 0:
    exit()

nvidia_install_path = os.path.join(temp_path, "nvidia")
cmd = "mkdir -p " + nvidia_install_path
if os.system(cmd) != 0:
    exit()

cmd = "mkdir -p " + os.path.join(nvidia_install_path, "usr/lib64/xorg/modules/{drivers,extensions}")
if os.system(cmd) != 0:
    exit()

cmd = "mkdir -p " + os.path.join(nvidia_install_path, "usr/bin")
if os.system(cmd) != 0:
    exit()

cmd = "mkdir -p " + os.path.join(nvidia_install_path, "etc")
if os.system(cmd) != 0:
    exit()

cmd = "mkdir -p " + os.path.join(nvidia_install_path, "lib/modules/" + unraid_uname + "/kernel/drivers/video")
if os.system(cmd) != 0:
    exit()

cmd = "mkdir -p " + os.path.join(nvidia_install_path, "lib/firmware")
if os.system(cmd) != 0:
    exit()


cmd = nvd_file_path + " --kernel-name="+unraid_uname
cmd += " --no-precompiled-interface" # 不使用预编译接口
cmd += " --kernel-source-path=" + kernel_src_path # 内核源码路径
# cmd += " --kernel-source-path=" + path + "/linux-5.19.17" # 内核源码路径
# cmd += " --kernel-source-path=/usr/src/linux" # 内核源码路径
cmd += " --disable-nouveau" # 禁用 nouveau
# 有些编译环境可能带了 opengl 相关的库，当 NVIDIA installer 检测到
# 系统中已经存在 opengl 相关的库时，会跳过安装 libglvnd，这会导致相关
# 的库文件无法正确安装，所以这里强制安装 libglvnd
cmd += " --install-libglvnd" # 安装 libglvnd
cmd += " --x-prefix=" + os.path.join(nvidia_install_path, "usr") # X11 安装路径
cmd += " --x-library-path=" + os.path.join(nvidia_install_path, "usr/lib64") # X11 库文件安装路径
cmd += " --x-module-path=" + os.path.join(nvidia_install_path, "usr/lib64/xorg/modules") # X11 模块安装路径
cmd += " --opengl-prefix=" + os.path.join(nvidia_install_path, "usr") # OpenGL 安装路径
cmd += " --installer-prefix=" + os.path.join(nvidia_install_path, "usr") # 安装程序安装路径
cmd += " --utility-prefix=" + os.path.join(nvidia_install_path, "usr") # 工具安装路径
cmd += " --documentation-prefix=" + os.path.join(nvidia_install_path, "usr") # 文档安装路径
cmd += " --application-profile-path=" + os.path.join(nvidia_install_path, "usr/share/nvidia") # 应用程序配置文件安装路径
cmd += " --proc-mount-point=" + os.path.join(nvidia_install_path, "proc") # proc 挂载点
cmd += " --kernel-install-path=" + os.path.join(nvidia_install_path, "lib/modules/" + unraid_uname + "/kernel/drivers/video") # 内核模块安装路径
cmd += " --compat32-prefix=" + os.path.join(nvidia_install_path, "usr") # 32 位兼容软件安装路径
cmd += " --compat32-libdir=/lib" # 32 位兼容库安装路径
cmd += " --install-compat32-libs" # 安装 32 位兼容库
cmd += " --no-x-check" # 不检查 X11
cmd += " --no-nouveau-check" # 不检查 nouveau
cmd += " --skip-depmod" # 跳过 depmod
cmd += " --j" + str(os.cpu_count()) # 使用所有 CPU 核心
cmd += " --silent" # 静默安装
print("Nvidia driver install cmd: " + cmd)
if os.system(cmd) != 0:
    exit()


if os.path.exists("/lib/firmware/nvidia"):
    cmd = "cp -R /lib/firmware/nvidia " + os.path.join(nvidia_install_path, "lib/firmware")
    if os.system(cmd) != 0:
        exit()

cmd = "cp /usr/bin/nvidia-modprobe " + os.path.join(nvidia_install_path, "usr/bin")
if os.system(cmd) != 0:
    exit()

cmd = "cp -R /etc/OpenCL " + os.path.join(nvidia_install_path, "etc")
if os.system(cmd) != 0:
    exit()

cmd = "cp -R /etc/vulkan " + os.path.join(nvidia_install_path, "etc")
if os.system(cmd) != 0:
    exit()

cmd = "cp -R /etc/nvidia " + os.path.join(nvidia_install_path, "etc")
if os.system(cmd) != 0:
    exit()

cmd = "mkdir -p " + os.path.join(nvidia_install_path, "etc", "nvidia", "ClientConfigToken")
if os.system(cmd) != 0:
    exit()


# 获取 https://github.com/ich777/libnvidia-container 的最新版本
json_data = subprocess.run(["curl","-sL","https://api.github.com/repos/ich777/libnvidia-container/releases/latest",],capture_output=True,text=True,).stdout
libnvidia_latest_version = json.loads(json_data)["tag_name"]
if libnvidia_latest_version == "" or libnvidia_latest_version == None:
    print("Failed to get latest version of libnvidia-container, exiting...")
    exit()
print("Latest version of libnvidia-container: " + libnvidia_latest_version)

if not os.path.exists(os.path.join(temp_path, "libnvidia-container-v" + libnvidia_latest_version + ".tar.gz")):
    cmd = ("wget --show-progress --progress=bar:force:noscroll -O " + os.path.join(temp_path, "libnvidia-container-v" + libnvidia_latest_version + ".tar.gz") + " https://github.com/ich777/libnvidia-container/releases/download/" + libnvidia_latest_version + "/libnvidia-container-v" + libnvidia_latest_version + ".tar.gz")
    if os.system(cmd) != 0:
        exit()

# 解压 libnvidia-container
cmd = ("tar -C " + nvidia_install_path + " -xf " + os.path.join(temp_path, "libnvidia-container-v" + libnvidia_latest_version + ".tar.gz"))
if os.system(cmd) != 0:
    exit()


# 获取 https://github.com/ich777/nvidia-container-toolkit 的最新版本
json_data = subprocess.run(["curl","-sL","https://api.github.com/repos/ich777/nvidia-container-toolkit/releases/latest",],capture_output=True,text=True,).stdout
container_toolkit_latest_version = json.loads(json_data)["tag_name"]
if container_toolkit_latest_version == "" or container_toolkit_latest_version == None:
    print("Failed to get latest version of nvidia-container-toolkit, exiting...")
    exit()
print("Latest version of nvidia-container-toolkit: " + container_toolkit_latest_version)

if not os.path.exists(os.path.join(temp_path,"nvidia-container-toolkit-v" + container_toolkit_latest_version + ".tar.gz",)):
    cmd = ("wget --show-progress --progress=bar:force:noscroll -O "+ os.path.join(temp_path,"nvidia-container-toolkit-v" + container_toolkit_latest_version + ".tar.gz",)+ " https://github.com/ich777/nvidia-container-toolkit/releases/download/"+ container_toolkit_latest_version+ "/nvidia-container-toolkit-v"+ container_toolkit_latest_version+ ".tar.gz")
    if os.system(cmd) != 0:
        exit()

# 解压 nvidia-container-toolkit
cmd = ("tar -C "+ nvidia_install_path+ " -xf "+ os.path.join(temp_path,"nvidia-container-toolkit-v" + container_toolkit_latest_version + ".tar.gz",))
if os.system(cmd) != 0:
    exit()
    

# Docker daemon.json 中加入镜像加速
daemon_path = os.path.join(nvidia_install_path,"etc","docker","daemon.json")
print("daemon_path: " + daemon_path)
origin_daemon = subprocess.run(["cat",daemon_path,],capture_output=True,text=True,).stdout
print("origin_daemon: " + origin_daemon)
# 查找倒数第二个 }
index = origin_daemon.rfind('}', 0, origin_daemon.rfind('}')) + 1
# 在倒数第二个 } 后面插入逗号
modified_daemon = origin_daemon[:index] + ',\n    \"registry-mirrors\": [\"https://mkggxy06.mirror.aliyuncs.com\"]' + origin_daemon[index:]
# 打开文件以追加模式
with open(daemon_path, 'w') as file:
    # 将内容追加到文件末尾
    file.write(modified_daemon)


if "grid" in nvd_file_name:
    cmd = "mkdir -p " + os.path.join(nvidia_install_path, "var", "lib", "nvidia", "GridLicensing")
    if os.system(cmd) != 0:
        exit()
    cmd = "mkdir -p " + os.path.join(nvidia_install_path, "etc", "nvidia", "nvidia", "GridLicensing", "data")
    if os.system(cmd) != 0:
        exit()


version = subprocess.run(["date", "+'%Y.%m.%d'"], capture_output=True, text=True).stdout.strip()
version_path = os.path.join(temp_path, "output/" + version)

cmd = "mkdir -p " + version_path
if os.system(cmd) != 0:
    exit()

cmd = "cp -R " + nvidia_install_path + "/* " + version_path
if os.system(cmd) != 0:
    exit()

cmd = "mkdir " + os.path.join(version_path, "install")
if os.system(cmd) != 0:
    exit()

plugin_name = "nvidia-driver"
nvidia_drv_version = "000.00.00"
pattern = r"\d+\.\d+\.\d+"
match = re.search(pattern, nvd_file_name)
if match:
    nvidia_drv_version = match.group()


cmd = """
tee {} <<EOF
|-----handy-ruler------------------------------------------------------|
nvidia-driver: nvidia-driver Package contents:
nvidia-driver:
nvidia-driver: Nvidia-Driver v{}
nvidia-driver: libnvidia-container v{}
nvidia-driver: nvidia-container-toolkit v{}
nvidia-driver:
nvidia-driver:
nvidia-driver: Custom {} for Unraid Kernel v{} by ich777
nvidia-driver:
EOF
""".format(version_path + "/install/slack-desc",nvidia_drv_version,libnvidia_latest_version,container_toolkit_latest_version,plugin_name,kernel_full_version,)

if os.system(cmd) != 0:
    exit()


cmd = "chmod +x " + os.path.join(path, "makepkg")
if os.system(cmd) != 0:
    exit()

driver_compact_out_path = os.path.join(temp_path, "output", "nvidia" + "-" + nvidia_drv_version + "-" + kernel_full_version + "-" + "Unraid" + "-" + "1.txz")
cmd ="cd " + version_path + " && " + os.path.join(path, "makepkg") + " -l n -c n " + driver_compact_out_path
print(cmd)
if os.system(cmd) != 0:
    exit()


# md5sum $TMP_DIR/${PLUGIN_NAME%%-*}-${NV_DRV_V}-${UNAME}-1.txz | awk '{print $1}' > $TMP_DIR/${PLUGIN_NAME%%-*}-${NV_DRV_V}-${UNAME}-1.txz.md5
cmd = "md5sum " + driver_compact_out_path + " | awk '{print $1}' > " + driver_compact_out_path + ".md5"
if os.system(cmd) != 0:
    exit()
