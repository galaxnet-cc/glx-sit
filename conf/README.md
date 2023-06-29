# 自动化测试拓朴

相关说明及设计见：https://docs.google.com/document/d/1lGOlfb6dCZOyAk1Jy4y5zA6ELY_Qwutrf3fDUbSycUc

# wsvm

wsvm是基于办公室物理机的虚拟拓朴。

相比hw拓朴，其接口更多。

tst拓朴中的LinuxIf1/3与DUT1相连， LinuxIf2/4与DUT4相连。

## 20230629 更新拓朴以支持单臂模式

tst linux5接入one-arm-br
dut1 wan5接入one-arm br
dut2 wan5接入uplink-br

详见自动化测试拓朴设计

# hw
