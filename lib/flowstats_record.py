import re
import json

from typing import List
from datetime import datetime


class Record:
    def __init__(self, destinationIPv4Address, destinationTransportPort, egressInterface, flowDirection,
                 flowEndNanoseconds, flowStartNanoseconds, glxAppId, glxRouteLabel, glxSegmentId, glxTrafficType,
                 ingressInterface, octetDeltaCount, packetDeltaCount, protocolIdentifier, sourceIPv4Address,
                 sourceTransportPort, tcpControlBits):
        self.destinationIPv4Address = destinationIPv4Address
        self.destinationTransportPort = destinationTransportPort
        self.egressInterface = egressInterface
        self.flowDirection = flowDirection
        self.flowEndNanoseconds = parse_isoformat_with_nanoseconds(flowEndNanoseconds)
        self.flowStartNanoseconds = parse_isoformat_with_nanoseconds(flowStartNanoseconds)
        self.glxAppId = glxAppId
        self.glxRouteLabel = glxRouteLabel
        self.glxSegmentId = glxSegmentId
        self.glxTrafficType = glxTrafficType
        self.ingressInterface = ingressInterface
        self.octetDeltaCount = octetDeltaCount
        self.packetDeltaCount = packetDeltaCount
        self.protocolIdentifier = protocolIdentifier
        self.sourceIPv4Address = sourceIPv4Address
        self.sourceTransportPort = sourceTransportPort
        self.tcpControlBits = tcpControlBits

class ExportedData:
    def __init__(self, exportTime, records: List[Record]):
        self.exportTime = datetime.fromisoformat(exportTime)
        self.records = records

def parse_isoformat_with_nanoseconds(time_str):
    # 使用正则表达式匹配 ISO 格式日期时间字符串，并捕获纳秒部分
    match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6})(\d+)?(.*)', time_str)
    if match:
        base_time = match.group(1)  # 基本时间部分，包含到微秒的精度
        # 可以根据需要处理时区信息，这里简单地取第三组匹配结果
        timezone = match.group(3) if match.group(3) else ''
        # 将基本时间部分与时区信息拼接，并转换为 datetime 对象
        return datetime.fromisoformat(f"{base_time}{timezone}")
    else:
        # 如果匹配失败，返回原始字符串（或者你可以选择抛出异常）
        return time_str

def parse_json_to_struct(json_data):
    parsed_data = json.loads(json_data)
    exported_data_list = []

    for data_block in parsed_data:
        records = []
        for record in data_block["records"]:
            record_obj = Record(**record)
            records.append(record_obj)
        exported_data = ExportedData(data_block["exportTime"], records)
        exported_data_list.append(exported_data)

    return exported_data_list
