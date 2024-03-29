## 系统依赖

 OS: ubuntu 20.04
 Python: python 3.6+
 PythonLibs: paramiko （可使用pip3 install -r requirements.txt安装)

## 办公室环境包重部署

### 前提
将本机public key加入所有目标dut的受信列表中。

另外，如果遇到ssh key不生效，可能是因为ubuntu 20.04上ssh-keygen生成的私钥是openssh的密钥格式，可用如下命令转换成
rsa格式：

```
ssh-keygen -p -m PEM -f ~/.ssh/id_rsa
```

### 配置
将conf目录的sitconf-example.json复制并改为sitconf.json，修改sitconf.json为自己的测试环境。

### 物理机sit环境部署

将待安装的包拷贝到miscs/redeploy_hw_1t_4d目录中的debs目录

```
cd misc/redeploy_hw_1t_4d/
./redeploy.sh
```

如果不进行出厂初始化，只更新包可以添加-f参数。

```
./redeploy.sh -f
```

### 复位实验环境（恢复出厂激活状态）

```
cd misc/redeploy_hw_1t_4d/
./redeploy.sh -r


```

### 虚拟机sit环境部署

将上述物理机redeploy_hw_1t_4d换成代码中相应的redeploy_wsvm_1t_4d即可

## 使用

方式0（makefile包装）


```
make test-basic
```

方式1/2本质上对于python unittest包的包装，可以直接参考python unittest包的文档了解如何执行测试用例，包括
执行特定用例（一个文件是一个测试集，代表一类测试例，一个test_*的类函数，则是一个具体的特试用例）。

方式1（手工执行特定测试class/test）：
```
python3 -m unittest testcases.single.test_rest_vpp_consistency_1d_glx.TestRestVppConsistency1DGlx.test_glx_link_block_wan_mode
```

方式2（文件执行）：

```
python3 -m unittest testcases/test_something.py
```

## 关于BUG

在测试用例中，如果因为BUG需要暂时workaround，需要在github上的vpp/fwdmd项目中增加issue，记录链接到用例中，以便后续解决后搜索优化用例。

## 待改进点

1. (DONE)~~topo对象支持读取配置文件。~~
2. (DONE)~~topo对象中的tst对象，连入topo的linux接口需支持读取配置文件。~~
