import time
import traceback

def glx_assert(condition):
    if not condition:
        stacks = ''
        for line in traceback.format_stack():
            stacks = stacks + line + ','
        print("assert failed in: " + stacks)
        # 5分钟左右，一般满足问题定位需求了
        time.sleep(300)
    return
