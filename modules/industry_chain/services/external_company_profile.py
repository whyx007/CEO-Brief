from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


WEAK_TERMS = {
    '材料', '新材料', '科技', '智能', '装备', '能源', '集团', '产业', '技术', '系统', '服务', '工程',
    '制造', '数字', '信息', '电子', '创新', '应用', '平台', '公司', '中心',
}

REGION_TERMS = [
    '北京', '上海', '天津', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽', '福建',
    '江西', '山东', '河南', '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海',
    '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门', '西安', '深圳', '广州', '苏州', '南京',
    '杭州', '成都', '武汉', '合肥', '青岛', '宁波', '厦门', '长沙', '郑州',
]

ORG_SUFFIX_PATTERN = re.compile(
    r'(股份有限公司|有限责任公司|有限公司|集团股份|集团有限公司|控股集团|控股有限公司|科技股份|科技有限公司|'
    r'股份|集团|控股|公司|厂|院|所|中心|大学|研究院|研究所|实验室)$'
)

DIMENSION_DEFINITIONS: dict[str, dict[str, str]] = {
    'supply_to_external': {
        'externalRole': 'buyer',
        'description': '被投企业向目标公司供应产品、设备、软件、服务或系统集成能力',
    },
    'external_supply_to_portfolio': {
        'externalRole': 'supplier',
        'description': '目标公司向被投企业提供材料、部件、平台、渠道或基础设施',
    },
    'joint_r_and_d': {
        'externalRole': 'partner',
        'description': '双方围绕能力互补、技术路线相邻或产品联合定义开展联合研发',
    },
    'shared_customer': {
        'externalRole': 'market_partner',
        'description': '双方服务同类下游客户或行业，可联合拓展市场',
    },
    'scenario_landing': {
        'externalRole': 'scenario_owner',
        'description': '目标公司提供真实应用场景，被投企业提供可落地能力',
    },
    'factory_or_operation_support': {
        'externalRole': 'operator',
        'description': '厂务、运营、能源、运维、安全、碳管理等配套合作',
    },
}


def _dimension(mode: str, terms: list[str]) -> dict[str, Any]:
    base = DIMENSION_DEFINITIONS[mode]
    return {
        'mode': mode,
        'externalRole': base['externalRole'],
        'description': base['description'],
        'queryTerms': _unique_terms(terms),
    }


def _unique_terms(values: list[Any] | tuple[Any, ...], limit: int | None = None) -> list[str]:
    result: list[str] = []
    for value in values:
        term = str(value or '').strip()
        if len(term) < 2 or term in result:
            continue
        result.append(term)
        if limit and len(result) >= limit:
            break
    return result


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


PROFILE_RULES: list[dict[str, Any]] = [
    {
        'id': 'power_grid',
        'markers': ('电网', '供电', '输电', '配电', '变电', '电力公司', '国家电网', '国网', '南方电网'),
        'industryDomains': ['能源电力', '电网运营'],
        'subSectors': ['输配电', '配网智能化', '新能源消纳', '电力设备运维'],
        'chainPosition': '运营方/应用方/客户方',
        'coreProducts': ['输配电网络运营', '供电服务', '电力调度'],
        'coreTechnologies': ['智能电网', '电力物联网', '配网自动化', '新能源并网'],
        'productionProcesses': ['发输变配用电调度', '设备巡检', '故障抢修', '负荷管理'],
        'upstreamNeeds': ['电力设备', '在线监测', '储能系统', '无人机巡检', '传感器', '虚拟电厂', '电力软件'],
        'downstreamApplications': ['工商业用电', '新能源消纳', '园区能源管理', '城市配网'],
        'targetCustomers': ['工商业用户', '园区', '新能源电站', '居民用户'],
        'painPoints': ['设备状态感知', '配网可靠性', '新能源消纳', '负荷峰谷波动', '安全巡检'],
        'dimensions': {
            'supply_to_external': ['电力设备', '变电', '配网', '储能', '在线监测', '传感器', '无人机巡检', '巡检机器人', '虚拟电厂', '电力软件'],
            'external_supply_to_portfolio': ['电网', '电力', '供电', '配电', '能源基础设施'],
            'joint_r_and_d': ['智能电网', '电力物联网', '新能源消纳', '配网自动化', '状态监测'],
            'shared_customer': ['工商业用户', '园区', '新能源电站', '电力客户'],
            'scenario_landing': ['变电站', '配电房', '输电线路', '新能源并网', '电力巡检'],
            'factory_or_operation_support': ['储能', '能碳管理', '安全监测', '运维', '应急电源'],
        },
    },
    {
        'id': 'automotive_oem',
        'markers': ('汽车', '车企', '主机厂', '整车', '乘用车', '商用车', '比亚迪', '吉利', '长安', '蔚来', '小鹏', '理想'),
        'industryDomains': ['汽车', '新能源汽车'],
        'subSectors': ['整车制造', '动力电池', '智能驾驶', '电驱电控', '补能生态'],
        'chainPosition': '中游/下游/客户方',
        'coreProducts': ['乘用车', '商用车', '新能源汽车', '动力电池系统'],
        'coreTechnologies': ['电池管理', '电驱动', '智能驾驶', '车载电子', '热管理'],
        'productionProcesses': ['整车研发', '零部件采购', '总装制造', '质量检测', '售后服务'],
        'upstreamNeeds': ['电池材料', '传感器', '车规芯片', '热管理', '轻量化材料', '检测设备', '充换电设备'],
        'downstreamApplications': ['出行服务', '物流运输', '储能', '充电网络'],
        'targetCustomers': ['个人消费者', '物流企业', '运营车队', '能源运营商'],
        'painPoints': ['电池安全', '续航效率', '智能化体验', '供应链稳定', '补能效率'],
        'dimensions': {
            'supply_to_external': ['电池材料', 'BMS', '热管理', '传感器', '激光雷达', '毫米波雷达', '车载芯片', '轻量化材料', '充电', '换电', '检测设备'],
            'external_supply_to_portfolio': ['汽车', '新能源汽车', '整车', '动力电池', '车载平台'],
            'joint_r_and_d': ['智能驾驶', '电池安全', '车载传感', '热管理', '轻量化'],
            'shared_customer': ['车企', '主机厂', '车队', '物流', '新能源汽车'],
            'scenario_landing': ['车载', '充换电', '自动驾驶', '电池检测', '储能'],
            'factory_or_operation_support': ['工厂物流', '能源管理', '储能', '安全巡检', '质量检测'],
        },
    },
    {
        'id': 'semiconductor_material',
        'markers': ('半导体材料', '硅片', '硅材料', '晶圆材料', '衬底', '外延', '奕斯伟材料'),
        'industryDomains': ['半导体', '电子材料'],
        'subSectors': ['半导体硅片', '晶圆材料', '衬底材料', '材料工艺'],
        'chainPosition': '上游/供应商',
        'coreProducts': ['半导体硅片', '衬底材料', '晶圆材料'],
        'coreTechnologies': ['晶体生长', '切磨抛清洗', '外延工艺', '材料检测'],
        'productionProcesses': ['拉晶', '切片', '研磨', '抛光', '清洗', '检测量测'],
        'upstreamNeeds': ['半导体设备', '检测量测', '洁净厂务', '高纯材料', '自动化搬运', '工艺软件'],
        'downstreamApplications': ['集成电路制造', '功率器件', '光电芯片', '硅光', 'Micro-LED'],
        'targetCustomers': ['晶圆厂', '芯片设计制造企业', '功率器件厂商', '光电芯片企业'],
        'painPoints': ['良率提升', '缺陷检测', '工艺稳定性', '国产替代', '客户认证周期'],
        'dimensions': {
            'supply_to_external': ['半导体设备', '检测量测', '晶圆检测', '缺陷检测', '洁净厂务', '自动化', '工艺软件', '高纯材料'],
            'external_supply_to_portfolio': ['硅片', '硅基', '衬底', '晶圆材料', '半导体材料', '外延'],
            'joint_r_and_d': ['材料工艺', '晶圆工艺', '硅光', '光电芯片', 'Micro-LED', '功率器件'],
            'shared_customer': ['晶圆厂', '半导体', '集成电路', '芯片制造', '光电芯片'],
            'scenario_landing': ['半导体制造', '晶圆检测', '封装测试', '光电芯片', '硅光'],
            'factory_or_operation_support': ['洁净室', '厂务', '能耗管理', '安全监测', '废气废水处理'],
        },
    },
    {
        'id': 'semiconductor',
        'markers': ('半导体', '芯片', '集成电路', '晶圆', '封装', '功率器件', '光电芯片'),
        'industryDomains': ['半导体', '集成电路'],
        'subSectors': ['芯片设计', '晶圆制造', '封装测试', '半导体设备材料'],
        'chainPosition': '上游/中游/供应商',
        'coreProducts': ['芯片', '功率器件', '传感器', '光电器件'],
        'coreTechnologies': ['芯片设计', '制造工艺', '封装测试', '检测量测'],
        'productionProcesses': ['设计', '制造', '封装', '测试', '认证'],
        'upstreamNeeds': ['EDA软件', '半导体设备', '硅片', '封装材料', '检测量测'],
        'downstreamApplications': ['汽车电子', '工业控制', '通信', '消费电子', '能源电力'],
        'targetCustomers': ['电子制造企业', '车企', '通信设备商', '工业客户'],
        'painPoints': ['国产替代', '可靠性验证', '先进封装', '供应链安全'],
        'dimensions': {
            'supply_to_external': ['半导体设备', '检测量测', 'EDA', '封装测试', '传感器', '光电芯片'],
            'external_supply_to_portfolio': ['芯片', '功率器件', '传感器', '半导体', '集成电路'],
            'joint_r_and_d': ['芯片设计', '封装', '测试', '可靠性', '光电集成'],
            'shared_customer': ['汽车电子', '工业控制', '通信', '消费电子'],
            'scenario_landing': ['车载', '工业控制', '通信网络', '电力电子'],
            'factory_or_operation_support': ['洁净室', '厂务', '能耗管理', '质量检测'],
        },
    },
    {
        'id': 'energy_storage',
        'markers': ('新能源', '储能', '风电', '光伏', '发电', '能源集团', '电池'),
        'industryDomains': ['新能源', '能源运营'],
        'subSectors': ['储能', '光伏', '风电', '能源管理', '电池系统'],
        'chainPosition': '运营方/应用方/供应商',
        'coreProducts': ['新能源发电', '储能系统', '能源管理服务'],
        'coreTechnologies': ['储能控制', '电池管理', '功率变换', '能量调度'],
        'productionProcesses': ['项目开发', '设备采购', '并网调度', '运维管理'],
        'upstreamNeeds': ['储能电池', 'PCS', 'BMS', '逆变器', '电力电子', '安全监测', '运维软件'],
        'downstreamApplications': ['新能源电站', '工商业储能', '微电网', '虚拟电厂'],
        'targetCustomers': ['电网公司', '园区', '工商业用户', '新能源业主'],
        'painPoints': ['安全性', '并网消纳', '收益模型', '运维效率'],
        'dimensions': {
            'supply_to_external': ['储能', 'BMS', 'PCS', '逆变器', '电池材料', '安全监测', '能源管理', '虚拟电厂'],
            'external_supply_to_portfolio': ['新能源', '储能', '光伏', '风电', '能源场景'],
            'joint_r_and_d': ['电池安全', '能量调度', '虚拟电厂', '新能源消纳'],
            'shared_customer': ['电网', '园区', '工商业', '新能源电站'],
            'scenario_landing': ['储能电站', '光伏电站', '微电网', '园区能源'],
            'factory_or_operation_support': ['安全监测', '运维巡检', '消防', '能碳管理'],
        },
    },
    {
        'id': 'data_center',
        'markers': ('数据中心', '智算', '算力', '云计算', '云厂商', 'AI中心', 'AI数据中心'),
        'industryDomains': ['数字基础设施', '算力服务'],
        'subSectors': ['数据中心', '智算中心', '云计算', '算力运维'],
        'chainPosition': '平台方/运营方/客户方',
        'coreProducts': ['算力服务', '数据中心托管', '云服务'],
        'coreTechnologies': ['服务器集群', '网络互联', '液冷散热', '电源管理', '运维监控'],
        'productionProcesses': ['机房建设', '设备采购', '资源调度', '运维监控', '能耗管理'],
        'upstreamNeeds': ['服务器', 'GPU', '光通信', '液冷', 'UPS', '储能', '网络设备', '运维监测'],
        'downstreamApplications': ['人工智能训练', '政企云', '工业互联网', '科研计算'],
        'targetCustomers': ['AI企业', '政府', '科研机构', '工业企业'],
        'painPoints': ['PUE能耗', '供电可靠性', '算力利用率', '网络带宽', '运维安全'],
        'dimensions': {
            'supply_to_external': ['液冷', '储能', 'UPS', '电源管理', '光通信', '网络互联', '服务器', '运维监测', '算力平台'],
            'external_supply_to_portfolio': ['算力', '云计算', '数据中心', 'AI平台'],
            'joint_r_and_d': ['液冷散热', '算力调度', '光通信', '网络互联', '能耗优化'],
            'shared_customer': ['AI企业', '政企客户', '科研机构', '工业互联网'],
            'scenario_landing': ['智算中心', '机房运维', 'AI训练', '边缘计算'],
            'factory_or_operation_support': ['温控', '储能', '电源', '消防安全', '能碳管理'],
        },
    },
    {
        'id': 'medical_institution',
        'markers': ('医院', '附属医院', '医疗机构', '疾控', '诊所', '医学中心'),
        'industryDomains': ['医疗健康', '医疗服务'],
        'subSectors': ['医院诊疗', '医学检测', '智慧医院', '医疗设备', '临床诊疗设备', '医院信息化'],
        'chainPosition': '应用方/客户方/场景方',
        'coreProducts': ['临床诊疗', '医学检测', '医疗服务', '科室诊疗', '住院与门诊服务'],
        'coreTechnologies': ['医学影像', '检验检测', '临床信息化', 'AI辅助诊断', '生命体征监测', '手术导航'],
        'productionProcesses': ['诊断', '治疗', '检测', '手术', '监护', '院内物流', '设备运维'],
        'upstreamNeeds': [
            '医疗设备', '体外诊断', '医学影像', '手术导航', '心电监测', '脑功能监护', 'PET-CT',
            '口腔医疗', '术中影像', '睡眠监测', '神经刺激', '核医学', '放疗设备', '耗材',
            'AI诊断', '医疗机器人', '院内物流',
        ],
        'downstreamApplications': ['患者服务', '临床科研', '区域医疗', '康复管理', '科室诊疗', '慢病管理'],
        'targetCustomers': ['患者', '医联体', '科研机构', '医保支付方'],
        'painPoints': ['诊疗效率', '检测准确性', '院内运营', '设备国产替代', '数据治理'],
        'dimensions': {
            'supply_to_external': [
                '冠脉OCT', 'OCT', '心电贴', '心电监测', '脑功能监护', '医学影像', '术中影像',
                '体外诊断', 'IVD', 'PET-CT', '核医学', 'BNCT', 'RLT', '口腔医疗', '睡眠监测',
                '神经刺激', '微针', '透皮给药', '消毒器械', '核辐射', 'AI诊断', '医疗机器人',
                '院内物流', '医疗检测', '医疗设备',
            ],
            'external_supply_to_portfolio': ['临床场景', '医院', '医学数据', '患者服务', '临床科研', '样本资源'],
            'joint_r_and_d': ['临床验证', '临床试验', 'AI诊断', '医学检测', '医学影像', '生物材料', '医疗机器人', '核医学', '精准治疗'],
            'shared_customer': ['医院', '医疗机构', '三甲医院', '医联体', '基层医疗', '患者', '体检中心'],
            'scenario_landing': ['心内科', '神经内科', '麻醉科', 'ICU', '核医学科', '口腔科', '放疗科', '检验科', '皮肤科', '睡眠中心', '手术室', '临床试点', '智慧医院', '院内物流', '康复'],
            'factory_or_operation_support': ['院内运维', '安全管理', '能耗管理', '设备维保', '医院安防', '感控', '放射防护'],
        },
    },
    {
        'id': 'aerospace_defense',
        'markers': ('航天', '航空', '卫星', '火箭', '军工', '飞行器', '研究院', '院所'),
        'industryDomains': ['航空航天', '高端装备'],
        'subSectors': ['商业航天', '卫星应用', '测运控', '航空装备'],
        'chainPosition': '研发方/应用方/客户方',
        'coreProducts': ['卫星', '飞行器', '航天系统', '测运控服务'],
        'coreTechnologies': ['遥感通信', '测控导航', '高可靠电子', '复合材料', '精密制造'],
        'productionProcesses': ['研发设计', '试验验证', '总装集成', '发射运营'],
        'upstreamNeeds': ['高可靠器件', '传感器', '复合材料', '测控设备', '光通信', '仿真软件'],
        'downstreamApplications': ['遥感', '通信', '导航', '应急管理', '国防应用'],
        'targetCustomers': ['政府', '军工集团', '商业航天企业', '行业用户'],
        'painPoints': ['可靠性', '轻量化', '国产替代', '测试验证', '在轨运维'],
        'dimensions': {
            'supply_to_external': ['卫星', '遥感', '测控', '光通信', '传感器', '高可靠器件', '复合材料', '仿真'],
            'external_supply_to_portfolio': ['航天场景', '试验验证', '院所', '卫星平台'],
            'joint_r_and_d': ['航天电子', '光通信', '遥感', '测运控', '轻量化'],
            'shared_customer': ['商业航天', '军工', '政府', '行业用户'],
            'scenario_landing': ['卫星应用', '测运控', '无人机', '应急通信'],
            'factory_or_operation_support': ['试验检测', '安全监测', '洁净厂房', '可靠性测试'],
        },
    },
    {
        'id': 'chemical_material',
        'markers': ('化工', '新材料', '复合材料', '膜材料', '陶瓷材料', '高分子', '材料科技'),
        'industryDomains': ['化工新材料', '先进材料'],
        'subSectors': ['功能材料', '复合材料', '高分子材料', '膜材料'],
        'chainPosition': '上游/供应商',
        'coreProducts': ['功能材料', '复合材料', '高分子材料'],
        'coreTechnologies': ['材料配方', '合成工艺', '改性加工', '检测评价'],
        'productionProcesses': ['研发配方', '中试放大', '生产加工', '质量检测'],
        'upstreamNeeds': ['原料', '工艺设备', '检测设备', '自动化产线', '环保安全'],
        'downstreamApplications': ['电子', '汽车', '能源', '环保', '装备制造'],
        'targetCustomers': ['制造企业', '能源企业', '电子企业', '环保客户'],
        'painPoints': ['客户认证', '规模化量产', '一致性', '环保安全'],
        'dimensions': {
            'supply_to_external': ['工艺设备', '检测设备', '自动化', '环保安全', '质量检测'],
            'external_supply_to_portfolio': ['功能材料', '复合材料', '高分子', '膜材料', '陶瓷材料'],
            'joint_r_and_d': ['材料配方', '改性', '复合材料', '导热', '导电', '过滤'],
            'shared_customer': ['汽车', '电子', '能源', '环保', '装备制造'],
            'scenario_landing': ['材料验证', '中试', '量产导入', '环保处理'],
            'factory_or_operation_support': ['环保', '安全监测', '能耗管理', '设备运维'],
        },
    },
    {
        'id': 'rail_transport',
        'markers': ('轨交', '轨道交通', '铁路', '地铁', '交通集团'),
        'industryDomains': ['轨道交通', '交通运营'],
        'subSectors': ['铁路运维', '城市轨交', '交通安全', '车站运营'],
        'chainPosition': '运营方/客户方/场景方',
        'coreProducts': ['轨道交通运营', '铁路运输', '车站服务'],
        'coreTechnologies': ['列车控制', '通信信号', '状态监测', '安全运维'],
        'productionProcesses': ['线路运营', '设备巡检', '安全调度', '乘客服务'],
        'upstreamNeeds': ['通信信号', '传感器', '安全监测', '巡检机器人', '电力设备', '运维软件'],
        'downstreamApplications': ['城市交通', '物流运输', '公共安全'],
        'targetCustomers': ['乘客', '物流客户', '地方政府'],
        'painPoints': ['安全可靠', '设备老化', '巡检效率', '客流调度'],
        'dimensions': {
            'supply_to_external': ['轨道交通', '铁路', '通信信号', '传感器', '安全监测', '巡检机器人', '电力设备', '运维软件'],
            'external_supply_to_portfolio': ['交通场景', '铁路客户', '轨交平台'],
            'joint_r_and_d': ['状态监测', '安全运维', '通信信号', '智能巡检'],
            'shared_customer': ['轨交', '铁路', '交通运营', '政府'],
            'scenario_landing': ['车站', '线路巡检', '隧道', '车辆段'],
            'factory_or_operation_support': ['电力运维', '安全监测', '应急通信', '能耗管理'],
        },
    },
    {
        'id': 'industrial_manufacturing',
        'markers': ('制造', '装备', '工业', '自动化', '智能制造', '机械'),
        'industryDomains': ['工业制造', '高端装备'],
        'subSectors': ['智能制造', '工业自动化', '装备制造', '质量检测'],
        'chainPosition': '中游/客户方/供应商',
        'coreProducts': ['工业产品', '装备系统', '制造服务'],
        'coreTechnologies': ['自动化控制', '机器视觉', '工业软件', '质量检测'],
        'productionProcesses': ['研发设计', '采购生产', '质量检测', '设备运维'],
        'upstreamNeeds': ['自动化设备', '传感器', '机器视觉', '工业软件', '检测设备', '机器人'],
        'downstreamApplications': ['汽车', '电子', '能源', '航空航天', '轨交'],
        'targetCustomers': ['制造企业', '装备客户', '行业集成商'],
        'painPoints': ['降本增效', '质量一致性', '柔性生产', '设备运维'],
        'dimensions': {
            'supply_to_external': ['自动化', '机器人', '机器视觉', '检测设备', '传感器', '工业软件', '设备运维'],
            'external_supply_to_portfolio': ['装备制造', '工业场景', '制造能力'],
            'joint_r_and_d': ['智能制造', '机器视觉', '工业软件', '自动化控制'],
            'shared_customer': ['制造企业', '汽车', '电子', '能源', '装备'],
            'scenario_landing': ['智能工厂', '产线检测', '设备运维', '仓储物流'],
            'factory_or_operation_support': ['能源管理', '安全监测', '预测性维护', '质量检测'],
        },
    },
]


def _company_aliases(company_name: str) -> list[str]:
    compact = re.sub(r'\s+', '', company_name)
    aliases = [compact] if compact else []
    without_suffix = ORG_SUFFIX_PATTERN.sub('', compact)
    if without_suffix and without_suffix != compact:
        aliases.append(without_suffix)
    for region in REGION_TERMS:
        if region in compact:
            aliases.append(region)
            rest = ORG_SUFFIX_PATTERN.sub('', compact.replace(region, ''))
            if len(rest) >= 2:
                aliases.append(rest)
    parts = [part for part in re.split(r'[省市区县集团控股股份有限责任公司（）()]+', compact) if len(part) >= 2]
    aliases.extend(parts)
    return _unique_terms(aliases, 10)


def _matching_rules(company_name: str) -> list[dict[str, Any]]:
    compact = re.sub(r'\s+', '', company_name)
    matches = [rule for rule in PROFILE_RULES if _contains_any(compact, tuple(rule['markers']))]
    if matches:
        return matches
    return []


def _fallback_rule(company_name: str) -> dict[str, Any]:
    aliases = _company_aliases(company_name)
    terms = [term for term in aliases if term not in WEAK_TERMS]
    return {
        'id': 'generic_external_company',
        'markers': (),
        'industryDomains': ['待识别行业'],
        'subSectors': ['待识别细分赛道'],
        'chainPosition': '目标公司/待识别',
        'coreProducts': terms[:3],
        'coreTechnologies': [],
        'productionProcesses': [],
        'upstreamNeeds': ['设备', '材料', '软件', '服务', '系统集成'],
        'downstreamApplications': [],
        'targetCustomers': [],
        'painPoints': ['需补充企业业务画像'],
        'dimensions': {
            'supply_to_external': terms + ['设备', '软件', '服务', '系统集成'],
            'external_supply_to_portfolio': terms,
            'joint_r_and_d': terms,
            'shared_customer': terms,
            'scenario_landing': terms,
            'factory_or_operation_support': ['能源管理', '安全监测', '运维', '检测'],
        },
    }


def build_external_company_profile(company_name: str) -> dict[str, Any]:
    name = str(company_name or '').strip()
    aliases = _company_aliases(name)
    rules = _matching_rules(name) or [_fallback_rule(name)]
    merged: dict[str, Any] = {
        'companyName': name,
        'aliases': aliases,
        'industryDomains': [],
        'subSectors': [],
        'chainPosition': '',
        'coreProducts': [],
        'coreTechnologies': [],
        'productionProcesses': [],
        'upstreamNeeds': [],
        'downstreamApplications': [],
        'targetCustomers': [],
        'painPoints': [],
        'cooperationDimensions': [],
        'weakTerms': [],
        'strongTerms': [],
        'profileSource': 'rules',
        'matchedRules': [rule['id'] for rule in rules],
    }
    dimension_terms: dict[str, list[str]] = {mode: [] for mode in DIMENSION_DEFINITIONS}
    chain_positions: list[str] = []
    for rule in rules:
        rule_copy = deepcopy(rule)
        for field in (
            'industryDomains', 'subSectors', 'coreProducts', 'coreTechnologies', 'productionProcesses',
            'upstreamNeeds', 'downstreamApplications', 'targetCustomers', 'painPoints',
        ):
            merged[field].extend(rule_copy.get(field) or [])
        chain_positions.append(str(rule_copy.get('chainPosition') or '').strip())
        for mode, terms in (rule_copy.get('dimensions') or {}).items():
            if mode in dimension_terms:
                dimension_terms[mode].extend(terms)
    merged['chainPosition'] = ' / '.join(_unique_terms(chain_positions)) or '目标公司/待识别'
    for field in (
        'industryDomains', 'subSectors', 'coreProducts', 'coreTechnologies', 'productionProcesses',
        'upstreamNeeds', 'downstreamApplications', 'targetCustomers', 'painPoints',
    ):
        merged[field] = _unique_terms(merged[field], 16)

    all_terms = (
        merged['coreProducts'] + merged['coreTechnologies'] + merged['productionProcesses'] +
        merged['upstreamNeeds'] + merged['downstreamApplications'] + merged['targetCustomers'] +
        merged['subSectors'] + [term for values in dimension_terms.values() for term in values]
    )
    strong_terms = [term for term in _unique_terms(all_terms, 48) if term not in WEAK_TERMS]
    weak_terms = [term for term in _unique_terms(aliases + all_terms, 48) if term in WEAK_TERMS]
    for alias in aliases:
        if alias in WEAK_TERMS:
            weak_terms.append(alias)
    merged['strongTerms'] = _unique_terms(strong_terms, 48)
    merged['weakTerms'] = _unique_terms(weak_terms, 24)

    dimensions = []
    for mode in DIMENSION_DEFINITIONS:
        terms = _unique_terms(dimension_terms.get(mode, []), 18)
        strong_first = [term for term in terms if term in merged['strongTerms']]
        rest = [term for term in terms if term not in strong_first]
        dimensions.append(_dimension(mode, strong_first + rest))
    merged['cooperationDimensions'] = dimensions
    return merged


def flatten_profile_query_terms(profile: dict[str, Any], limit: int = 80) -> list[str]:
    terms: list[str] = []
    terms.extend(profile.get('strongTerms') or [])
    for dimension in profile.get('cooperationDimensions') or []:
        if isinstance(dimension, dict):
            terms.extend(dimension.get('queryTerms') or [])
    return _unique_terms(terms, limit)
