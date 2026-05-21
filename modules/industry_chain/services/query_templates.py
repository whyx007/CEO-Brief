from __future__ import annotations

STATUS_COUNTS = """
MATCH (n)
UNWIND labels(n) AS label
WITH label, count(*) AS count
ORDER BY count DESC
RETURN collect({label: label, count: count}) AS nodeCounts
"""

STATUS_REL_COUNTS = """
MATCH ()-[r]->()
WITH type(r) AS relationshipType, count(*) AS count
ORDER BY count DESC
RETURN collect({relationshipType: relationshipType, count: count}) AS relationshipCounts
"""

SUB_TRACKS = """
MATCH (s:SubTrack)
OPTIONAL MATCH (s)-[:HAS_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e:Enterprise)-[:LOCATED_IN_STAGE]->(st)
RETURN s.id AS id,
       s.name AS name,
       s.description AS description,
       count(DISTINCT st) AS stageCount,
       count(DISTINCT e) AS enterpriseCount
ORDER BY id
"""

OVERVIEW = """
MATCH (s:SubTrack)
OPTIONAL MATCH (s)-[:HAS_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e:Enterprise)-[:LOCATED_IN_STAGE]->(st)
WITH s, st, count(DISTINCT e) AS enterpriseCount, collect(DISTINCT e.name)[0..10] AS enterprises
RETURN s.id AS subTrackId,
       s.name AS subTrack,
       s.description AS subTrackDescription,
       st.id AS stageId,
       st.name AS stage,
       st.stage_level AS stageLevel,
       st.stage_order AS stageOrder,
       enterpriseCount,
       enterprises
ORDER BY subTrack, stageOrder
"""

COMPANY_UPDOWN = """
MATCH (e:Enterprise)
WHERE e.name CONTAINS $enterpriseName
WITH e
LIMIT $enterpriseLimit
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (up:ChainStage)-[:UPSTREAM_OF]->(st)
OPTIONAL MATCH (st)-[:UPSTREAM_OF]->(down:ChainStage)
OPTIONAL MATCH (upE:Enterprise)-[:LOCATED_IN_STAGE]->(up)
OPTIONAL MATCH (downE:Enterprise)-[:LOCATED_IN_STAGE]->(down)
OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
RETURN e.id AS enterpriseId,
       e.name AS enterprise,
       e.match_level AS matchLevel,
       collect(DISTINCT s.name) AS subTracks,
       collect(DISTINCT st.id) AS stageIds,
       collect(DISTINCT st.name) AS stages,
       collect(DISTINCT up.id) AS upstreamStageIds,
       collect(DISTINCT up.name) AS upstreamStages,
       collect(DISTINCT upE.name)[0..$limit] AS upstreamEnterprises,
       collect(DISTINCT CASE WHEN up.name IS NOT NULL AND upE.name IS NOT NULL THEN {stage: up.name, enterprise: upE.name} END)[0..$limit] AS upstreamRelations,
       collect(DISTINCT down.id) AS downstreamStageIds,
       collect(DISTINCT down.name) AS downstreamStages,
       collect(DISTINCT downE.name)[0..$limit] AS downstreamEnterprises,
       collect(DISTINCT CASE WHEN down.name IS NOT NULL AND downE.name IS NOT NULL THEN {stage: down.name, enterprise: downE.name} END)[0..$limit] AS downstreamRelations,
       collect(DISTINCT supplier.name)[0..$limit] AS suppliers,
       collect(DISTINCT customer.name)[0..$limit] AS customers,
       collect(DISTINCT k.name)[0..20] AS keyCapabilities
"""

OPPORTUNITIES_UPDOWN_BY_SUBTRACK = """
MATCH (s:SubTrack)
WHERE $scopeType = 'all' OR s.name CONTAINS $keyword OR s.id = $keyword
MATCH (s)-[:HAS_STAGE]->(up:ChainStage)-[:UPSTREAM_OF]->(down:ChainStage)
MATCH (a:Enterprise)-[:LOCATED_IN_STAGE]->(up)
MATCH (b:Enterprise)-[:LOCATED_IN_STAGE]->(down)
WHERE a <> b
OPTIONAL MATCH (a)-[:HAS_KEY_CAPABILITY]->(ak:KeyCapability)
OPTIONAL MATCH (b)-[:HAS_KEY_CAPABILITY]->(bk:KeyCapability)
RETURN a.name AS sourceEnterprise,
       b.name AS targetEnterprise,
       s.name AS subTrack,
       up.id AS sourceStageId,
       up.name AS sourceStage,
       down.id AS targetStageId,
       down.name AS targetStage,
       collect(DISTINCT ak.name)[0..5] AS sourceCapabilities,
       collect(DISTINCT bk.name)[0..5] AS targetCapabilities,
       'updown' AS opportunityType,
       'high' AS confidence
ORDER BY subTrack, sourceStage, targetStage, sourceEnterprise, targetEnterprise
LIMIT $limit
"""

OPPORTUNITIES_UPDOWN_BY_ENTERPRISE = """
MATCH (a:Enterprise)
WHERE a.name CONTAINS $keyword
MATCH (a)-[:LOCATED_IN_STAGE]->(stage:ChainStage)
OPTIONAL MATCH (stage)-[:UPSTREAM_OF]->(down:ChainStage)
OPTIONAL MATCH (downE:Enterprise)-[:LOCATED_IN_STAGE]->(down)
OPTIONAL MATCH (up:ChainStage)-[:UPSTREAM_OF]->(stage)
OPTIONAL MATCH (upE:Enterprise)-[:LOCATED_IN_STAGE]->(up)
OPTIONAL MATCH (a)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
WITH a, s, stage, collect(DISTINCT {enterprise: downE.name, stage: down.name, stageId: down.id, direction: 'downstream'}) +
                  collect(DISTINCT {enterprise: upE.name, stage: up.name, stageId: up.id, direction: 'upstream'}) AS pairs
UNWIND pairs AS pair
WITH a, s, stage, pair
WHERE pair.enterprise IS NOT NULL AND pair.enterprise <> a.name
RETURN CASE pair.direction WHEN 'upstream' THEN pair.enterprise ELSE a.name END AS sourceEnterprise,
       CASE pair.direction WHEN 'upstream' THEN a.name ELSE pair.enterprise END AS targetEnterprise,
       s.name AS subTrack,
       CASE pair.direction WHEN 'upstream' THEN pair.stageId ELSE stage.id END AS sourceStageId,
       CASE pair.direction WHEN 'upstream' THEN pair.stage ELSE stage.name END AS sourceStage,
       CASE pair.direction WHEN 'upstream' THEN stage.id ELSE pair.stageId END AS targetStageId,
       CASE pair.direction WHEN 'upstream' THEN stage.name ELSE pair.stage END AS targetStage,
       [] AS sourceCapabilities,
       [] AS targetCapabilities,
       'updown' AS opportunityType,
       'high' AS confidence
LIMIT $limit
"""

OPPORTUNITIES_SCENARIO = """
MATCH (scenario:ApplicationScenario)
WHERE $scopeType = 'all' OR scenario.name CONTAINS $keyword OR scenario.description CONTAINS $keyword
MATCH (scenario)-[:DRIVES_STAGE]->(st:ChainStage)<-[:LOCATED_IN_STAGE]-(e:Enterprise)
WITH scenario, collect(DISTINCT e.name)[0..30] AS enterprises
UNWIND enterprises AS sourceEnterprise
UNWIND enterprises AS targetEnterprise
WITH scenario, sourceEnterprise, targetEnterprise
WHERE sourceEnterprise < targetEnterprise
RETURN sourceEnterprise,
       targetEnterprise,
       scenario.name AS scenario,
       'scenario_joint' AS opportunityType,
       'medium' AS confidence
LIMIT $limit
"""

OPPORTUNITIES_EXTERNAL_COMPANY = """
MATCH (e:Enterprise)
WHERE any(term IN $queryTerms WHERE e.name CONTAINS term)
   OR EXISTS {
       MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
       WHERE any(term IN $queryTerms WHERE s.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
       WHERE any(term IN $queryTerms WHERE st.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT]->(cap)
       WHERE any(term IN $queryTerms WHERE cap.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
       WHERE any(term IN $queryTerms WHERE tag.name CONTAINS term)
   }
WITH DISTINCT e
LIMIT $limit
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
WITH e, collect(DISTINCT s.name) AS subTracks, collect(DISTINCT st.name) AS stages,
     collect(DISTINCT k.name) AS keyCapabilities, collect(DISTINCT cap.name) AS capabilities,
     collect(DISTINCT product.name) AS products, collect(DISTINCT scenario.name) AS scenarios,
     collect(DISTINCT demand.name) AS demands, collect(DISTINCT industry.name) AS industries,
     collect(DISTINCT customer.name) AS customers, collect(DISTINCT supplier.name) AS suppliers
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers,
     keyCapabilities + capabilities + products AS targetCapabilities
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       targetCapabilities[0..8] AS targetCapabilities,
       customers[0..5] AS customers,
       suppliers[0..5] AS suppliers,
       scenarios[0..5] AS scenarios,
       demands[0..5] AS demands,
       'external_company' AS opportunityType,
       CASE WHEN size(customers) + size(suppliers) > 0 THEN 'high' ELSE 'medium' END AS confidence
"""

OPPORTUNITIES_TECHNOLOGY_SCOPE = """
MATCH (e:Enterprise)
WHERE any(term IN $queryTerms WHERE e.name CONTAINS term)
   OR EXISTS {
       MATCH (e)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT]->(cap)
       WHERE any(term IN $queryTerms WHERE cap.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
       WHERE any(term IN $queryTerms WHERE st.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
       WHERE any(term IN $queryTerms WHERE s.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:APPLIES_TO_SCENARIO|HAS_DEMAND]->(tag)
       WHERE any(term IN $queryTerms WHERE tag.name CONTAINS term)
   }
WITH DISTINCT e
LIMIT $limit
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
WITH e, collect(DISTINCT k.name) AS keyCapabilities, collect(DISTINCT cap.name) AS capabilities,
     collect(DISTINCT product.name) AS products, collect(DISTINCT scenario.name) AS scenarios,
     collect(DISTINCT demand.name) AS demands, collect(DISTINCT st.name) AS stages,
     collect(DISTINCT s.name) AS subTracks
WITH e, subTracks, stages, scenarios, demands, keyCapabilities + capabilities + products AS targetCapabilities
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       targetCapabilities[0..8] AS targetCapabilities,
       scenarios[0..5] AS scenarios,
       demands[0..5] AS demands,
       'technology_scope' AS opportunityType,
       CASE WHEN any(term IN $queryTerms WHERE any(x IN targetCapabilities WHERE x IS NOT NULL AND x CONTAINS term)) THEN 'high' ELSE 'medium' END AS confidence
"""

OPPORTUNITIES_INDUSTRY_DIRECTION = """
MATCH (e:Enterprise)
WHERE EXISTS {
       MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
       WHERE any(term IN $queryTerms WHERE s.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
       WHERE any(term IN $queryTerms WHERE st.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT]->(cap)
       WHERE any(term IN $queryTerms WHERE cap.name CONTAINS term)
   }
   OR EXISTS {
       MATCH (e)-[:APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY]->(tag)
       WHERE any(term IN $queryTerms WHERE tag.name CONTAINS term)
   }
WITH DISTINCT e
LIMIT $limit
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scene:Scenario)
OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
OPTIONAL MATCH (scenario:ApplicationScenario)-[:DRIVES_STAGE]->(st)
WITH e, collect(DISTINCT s.name) AS subTracks, collect(DISTINCT st.name) AS stages,
     collect(DISTINCT k.name) AS keyCapabilities, collect(DISTINCT cap.name) AS capabilities,
     collect(DISTINCT product.name) AS products, collect(DISTINCT scene.name) AS profileScenarios,
     collect(DISTINCT demand.name) AS demands, collect(DISTINCT industry.name) AS industries,
     collect(DISTINCT scenario.name) AS graphScenarios
WITH e, subTracks, stages, demands, industries, graphScenarios + profileScenarios AS scenarios,
     keyCapabilities + capabilities + products AS targetCapabilities
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       targetCapabilities[0..8] AS targetCapabilities,
       scenarios[0..5] AS scenarios,
       demands[0..5] AS demands,
       'industry_direction' AS opportunityType,
       CASE WHEN any(term IN $queryTerms WHERE any(x IN scenarios WHERE x IS NOT NULL AND x CONTAINS term)) THEN 'high' ELSE 'medium' END AS confidence
"""
