import time
import traceback

def glx_assert(condition):
    if not condition:
        stacks = ''
        for line in traceback.format_stack():
            stacks = stacks + line + ','
        print("assert failed in: " + stacks)
        time.sleep(1000)
    return