class Dut:
    def __init__(self, name):
        self.name = name

    def set_if_map(self, if_map):
        self.if_map = if_map

    def get_if_map(self):
        return self.if_map

    def set_rest_device(self, rest_device):
        self.rest_device = rest_device

    def get_rest_device(self):
        return self.rest_device

    def set_vpp_ssh_device(self, vpp_ssh_device):
        self.vpp_ssh_device = vpp_ssh_device

    def get_vpp_ssh_device(self):
        return self.vpp_ssh_device
