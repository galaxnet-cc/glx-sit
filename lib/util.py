import time
import traceback
import inspect

def glx_assert(condition):
    if not condition:
        stacks = ''
        for line in traceback.format_stack():
            stacks = stacks + line + ','
        print("assert failed in: " + stacks)
        out_frame = inspect.getouterframes(inspect.currentframe())
        #print("frame: ", out_frame[1].frame)
        argvalues = inspect.getargvalues(out_frame[1].frame)
        # 将断言失败的参数也打印出来，方便分析问题，避免重跑
        print("assert context: ", argvalues)
        # 5分钟左右，一般满足问题定位需求了
        time.sleep(300)
    return
