"""
================================================================================
 合作方向分析 —— 针对你的程序的改进参考
 问题诊断 + 改进方案
================================================================================
 你当前程序的问题（从你给的报告看出）：
 1. 用 "设备""软件""系统集成" 等泛词做匹配 -> 制氧机公司也能命中雷达公司
 2. 没有利用 Neo4j 的图结构 -> 只做文本关键词匹配
 3. 排名靠 "泛词命中数量" -> 制氧机公司反而排A级
 
 改进方案核心：
 用 Neo4j 的关系（SERVES_INDUSTRY / APPLIES_TO_SCENARIO / HAS_CAPABILITY）
 替代文本关键词匹配
================================================================================
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from neo4j import GraphDatabase

NEO4J_URI = "bolt://192.168.10.61:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j2026"


def get_target_profile(driver, company_name: str) -> dict:
    """获取目标公司的完整画像"""
    with driver.session() as session:
        # 1. 能力
        caps = session.run("""
            MATCH (e:Enterprise {name: $name})-[:HAS_CAPABILITY]->(c:Capability)
            RETURN c.name AS name
        """, name=company_name)
        capabilities = [r["name"] for r in caps]

        # 2. 行业
        inds = session.run("""
            MATCH (e:Enterprise {name: $name})-[:SERVES_INDUSTRY]->(i:Industry)
            RETURN i.name AS name
        """, name=company_name)
        industries = [r["name"] for r in inds]

        # 3. 场景
        scs = session.run("""
            MATCH (e:Enterprise {name: $name})-[:APPLIES_TO_SCENARIO]->(s:Scenario)
            RETURN s.name AS name
        """, name=company_name)
        scenarios = [r["name"] for r in scs]

        # 4. 产品
        prods = session.run("""
            MATCH (e:Enterprise {name: $name})-[:PROVIDES_PRODUCT]->(p:Product)
            RETURN p.name AS name
        """, name=company_name)
        products = [r["name"] for r in prods]

        # 5. 客户
        custs = session.run("""
            MATCH (e:Enterprise {name: $name})-[:HAS_CUSTOMER]->(c:Customer)
            RETURN c.name AS name
        """, name=company_name)
        customers = [r["name"] for r in custs]

        # 6. 供应商需求
        sups = session.run("""
            MATCH (e:Enterprise {name: $name})-[:HAS_SUPPLIER]->(s:Supplier)
            RETURN s.name AS name
        """, name=company_name)
        suppliers = [r["name"] for r in sups]

        return {
            "capabilities": capabilities,
            "industries": industries,
            "scenarios": scenarios,
            "products": products,
            "customers": customers,
            "suppliers": suppliers,
        }


# ============================================================
#  改进1：用图关系替代文本关键词匹配
# ============================================================

def find_by_graph_relations(driver, target_name: str, profile: dict):
    """
    核心改进：不走"文本关键词匹配"，走 Neo4j 图关系。
    
    思路：先找"中科慧智"所在的节点（行业/场景/能力），
    再找"共享这些节点"的其他企业。
    这才是真正的"同行业/同场景/能力相关"。
    """

    # --- 方向1：同行业企业（共享 Industry 节点）---
    print("\n>> 方向1: 同行业企业（通过 SERVES_INDUSTRY 关系）")
    with driver.session() as session:
        industries = profile.get("industries", [])
        if industries:
            result = session.run("""
                MATCH (target:Enterprise {name: $target})-[:SERVES_INDUSTRY]->(ind:Industry)
                MATCH (partner:Enterprise)-[:SERVES_INDUSTRY]->(ind)
                WHERE partner.name <> $target
                WITH partner, ind, count(*) AS weight
                OPTIONAL MATCH (partner)-[:HAS_CAPABILITY]->(cap:Capability)
                RETURN partner.name AS 企业,
                       collect(DISTINCT ind.name) AS 共享行业,
                       collect(DISTINCT cap.name)[..5] AS 能力
                ORDER BY size(collect(DISTINCT ind.name)) DESC
                LIMIT 10
            """, target=target_name)
            has_result = False
            for r in result:
                has_result = True
                print(f"  {r['企业']}")
                print(f"    共享行业: {r['共享行业']}")
            if not has_result:
                print("  (无结果 - 该企业可能没有其他同行业伙伴)")
        else:
            print("  (目标公司没有行业信息)")

    # --- 方向2：同场景企业（共享 Scenario 节点）---
    print("\n>> 方向2: 同场景企业（通过 APPLIES_TO_SCENARIO 关系）")
    with driver.session() as session:
        scenarios = profile.get("scenarios", [])
        if scenarios:
            result = session.run("""
                MATCH (target:Enterprise {name: $target})-[:APPLIES_TO_SCENARIO]->(sc:Scenario)
                MATCH (partner:Enterprise)-[:APPLIES_TO_SCENARIO]->(sc)
                WHERE partner.name <> $target
                WITH partner, sc, count(*) AS weight
                OPTIONAL MATCH (partner)-[:HAS_CAPABILITY]->(cap:Capability)
                RETURN partner.name AS 企业,
                       collect(DISTINCT sc.name) AS 共享场景,
                       collect(DISTINCT cap.name)[..5] AS 能力
                ORDER BY size(collect(DISTINCT sc.name)) DESC
                LIMIT 10
            """, target=target_name)
            has_result = False
            for r in result:
                has_result = True
                print(f"  {r['企业']}")
                print(f"    共享场景: {r['共享场景']}")
            if not has_result:
                print("  (无结果 - 该企业场景是独特的，无其他企业共享)")
        else:
            print("  (目标公司没有场景信息)")

    # --- 方向3：能力关键词匹配（只查 Capability 节点，不查泛词）---
    print("\n>> 方向3: 能力关键词匹配（只查 Capability 节点）")
    with driver.session() as session:
        # 只用专业关键词，不用"设备""软件""系统集成"等泛词
        keywords = ["雷达", "安防", "探测", "军工", "光电", "红外", "射频",
                    "微波", "预警", "防御", "无人机", "反制", "感知", "安检"]
        conditions = " OR ".join([f"c.name CONTAINS '{kw}'" for kw in keywords])
        result = session.run(f"""
            MATCH (e:Enterprise)-[:HAS_CAPABILITY]->(c:Capability)
            WHERE ({conditions}) AND e.name <> $target
            WITH e, collect(DISTINCT c.name) AS matched_caps
            OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(ind:Industry)
            RETURN e.name AS 企业,
                   matched_caps AS 匹配能力,
                   collect(DISTINCT ind.name)[..3] AS 行业
            ORDER BY size(matched_caps) DESC
            LIMIT 10
        """, target=target_name)
        for r in result:
            print(f"  {r['企业']}")
            print(f"    匹配能力: {r['匹配能力'][:3]}")
            print(f"    行业: {r['行业']}")

    # --- 方向4：军工/国防客户重叠 ---
    print("\n>> 方向4: 军工/国防客户重叠")
    with driver.session() as session:
        customer_kw = ["军工", "军队", "国防", "公安", "部队", "低空", "反无人机"]
        conditions = " OR ".join([f"c.name CONTAINS '{kw}'" for kw in customer_kw])
        result = session.run(f"""
            MATCH (e:Enterprise)-[:HAS_CUSTOMER]->(c:Customer)
            WHERE ({conditions}) AND e.name <> $target
            WITH e, collect(DISTINCT c.name) AS key_customers
            OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
            RETURN e.name AS 企业,
                   key_customers AS 军工客户,
                   collect(DISTINCT cap.name)[..3] AS 能力
            ORDER BY size(key_customers) DESC
            LIMIT 10
        """, target=target_name)
        for r in result:
            print(f"  {r['企业']}")
            print(f"    军工客户: {r['军工客户']}")
            print(f"    能力: {r['能力']}")


# ============================================================
#  主流程
# ============================================================

def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    target = "珠海中科慧智科技有限公司"

    print("=" * 60)
    print(f"  目标公司: {target}")
    print("=" * 60)

    # 1. 画像
    print("\n[Step 1] 获取目标公司画像...")
    profile = get_target_profile(driver, target)
    print(f"  能力: {len(profile.get('capabilities', []))} 项 -> {profile['capabilities']}")
    print(f"  行业: {len(profile.get('industries', []))} 个")
    print(f"  场景: {len(profile.get('scenarios', []))} 个")
    print(f"  客户: {len(profile.get('customers', []))} 个")
    print(f"  供应商需求: {profile.get('suppliers', [])}")

    # 2. 用图关系做匹配（替代文本泛词）
    print("\n[Step 2] 用 Neo4j 图关系做匹配...")
    find_by_graph_relations(driver, target, profile)

    print("\n" + "=" * 60)
    print("  对比你的程序：")
    print("  - 你的程序匹配到 '中科汇智(制氧机)' 因为泛词'设备'")
    print("  - 这个程序通过图关系匹配，只会找到真正同行业/同场景的企业")
    print("=" * 60)

    driver.close()


if __name__ == "__main__":
    main()
