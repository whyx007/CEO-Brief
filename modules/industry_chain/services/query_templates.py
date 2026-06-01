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

ENTERPRISE_PROFILE_BY_NAME = """
MATCH (e:Enterprise)
WHERE e.name = $keyword OR e.name CONTAINS $keyword OR $keyword CONTAINS e.name
WITH e
ORDER BY size(e.name) DESC
LIMIT 3
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
RETURN e.name AS enterprise,
       subTracks[0..8] AS subTracks,
       stages[0..8] AS stages,
       keyCapabilities[0..8] AS keyCapabilities,
       capabilities[0..10] AS capabilities,
       products[0..10] AS products,
       customers[0..10] AS customers,
       scenarios[0..10] AS scenarios,
       industries[0..10] AS industries,
       demands[0..8] AS demands,
       suppliers[0..8] AS suppliers
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
WHERE any(term IN $primaryTerms WHERE e.name CONTAINS term)
WITH e, 40 AS baseScore
LIMIT $candidateLimit
WITH collect({enterprise: e, score: baseScore}) AS directCandidates
CALL {
  MATCH (e:Enterprise)-[r:HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
  WHERE any(term IN $queryTerms WHERE tag.name CONTAINS term)
  WITH e, r, tag,
       CASE WHEN any(term IN $anchorTerms WHERE tag.name CONTAINS term) THEN 1 ELSE 0 END AS anchorHit
  WITH e, max(CASE
    WHEN type(r) = 'HAS_CUSTOMER' AND anchorHit = 1 THEN 80
    WHEN type(r) = 'HAS_SUPPLIER' AND anchorHit = 1 THEN 55
    WHEN type(r) = 'HAS_CUSTOMER' THEN 36
    ELSE 24
  END) AS baseScore
  ORDER BY baseScore DESC, e.name
  LIMIT $candidateLimit
  RETURN collect({enterprise: e, score: baseScore}) AS relationshipCandidates
}
CALL {
  MATCH (e:Enterprise)-[r:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT|APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|FOCUSES_ON_SUB_TRACK|LOCATED_IN_STAGE]->(tag)
  WHERE any(term IN $queryTerms WHERE tag.name CONTAINS term)
  WITH e, max(CASE
    WHEN type(r) IN ['HAS_KEY_CAPABILITY', 'HAS_CAPABILITY', 'PROVIDES_PRODUCT'] THEN 18
    WHEN type(r) IN ['APPLIES_TO_SCENARIO', 'SERVES_INDUSTRY'] THEN 15
    ELSE 10
  END) AS baseScore
  ORDER BY baseScore DESC, e.name
  LIMIT $candidateLimit
  RETURN collect({enterprise: e, score: baseScore}) AS profileCandidates
}
WITH directCandidates + relationshipCandidates + profileCandidates AS candidates
UNWIND candidates AS candidate
WITH candidate.enterprise AS e, max(candidate.score) AS baseScore
ORDER BY baseScore DESC, e.name
LIMIT $candidateLimit
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers,
     keyCapabilities + capabilities + products AS targetCapabilities,
     baseScore
WITH e, subTracks, stages, targetCapabilities, scenarios, demands, industries, customers, suppliers,
     baseScore
     + reduce(score = 0, term IN $primaryTerms |
       score
       + CASE WHEN e.name CONTAINS term THEN 30 ELSE 0 END
       + CASE WHEN any(x IN customers WHERE x IS NOT NULL AND x CONTAINS term) THEN 30 ELSE 0 END
       + CASE WHEN any(x IN suppliers WHERE x IS NOT NULL AND x CONTAINS term) THEN 20 ELSE 0 END
     )
     + reduce(score = 0, term IN $anchorTerms |
       score
       + CASE WHEN any(x IN customers WHERE x IS NOT NULL AND x CONTAINS term) THEN 35 ELSE 0 END
       + CASE WHEN any(x IN suppliers WHERE x IS NOT NULL AND x CONTAINS term) THEN 20 ELSE 0 END
     )
     + reduce(score = 0, term IN $queryTerms |
       score
       + CASE WHEN any(x IN customers WHERE x IS NOT NULL AND x CONTAINS term) THEN 12 ELSE 0 END
       + CASE WHEN any(x IN suppliers WHERE x IS NOT NULL AND x CONTAINS term) THEN 8 ELSE 0 END
       + CASE WHEN any(x IN targetCapabilities WHERE x IS NOT NULL AND x CONTAINS term) THEN 6 ELSE 0 END
       + CASE WHEN any(x IN scenarios WHERE x IS NOT NULL AND x CONTAINS term) THEN 5 ELSE 0 END
       + CASE WHEN any(x IN industries WHERE x IS NOT NULL AND x CONTAINS term) THEN 5 ELSE 0 END
       + CASE WHEN any(x IN demands WHERE x IS NOT NULL AND x CONTAINS term) THEN 3 ELSE 0 END
       + CASE WHEN any(x IN subTracks WHERE x IS NOT NULL AND x CONTAINS term) THEN 3 ELSE 0 END
       + CASE WHEN any(x IN stages WHERE x IS NOT NULL AND x CONTAINS term) THEN 3 ELSE 0 END
     ) AS matchScore
ORDER BY matchScore DESC, e.name
LIMIT $limit
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       targetCapabilities[0..8] AS targetCapabilities,
       customers[0..5] AS customers,
       suppliers[0..5] AS suppliers,
       scenarios[0..5] AS scenarios,
       demands[0..5] AS demands,
       matchScore AS matchScore,
       'external_company' AS opportunityType,
       CASE WHEN matchScore >= 12 THEN 'high' ELSE 'medium' END AS confidence
"""

OPPORTUNITIES_EXTERNAL_COMPANY_MULTIDIMENSION = """
UNWIND $dimensionQueries AS dimension
WITH dimension
MATCH (e:Enterprise)
WHERE EXISTS {
       MATCH (e)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT|APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|FOCUSES_ON_SUB_TRACK|LOCATED_IN_STAGE|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
       WHERE tag.name IS NOT NULL
         AND any(term IN dimension.queryTerms WHERE tag.name CONTAINS term)
   }
WITH DISTINCT e
LIMIT $candidateLimit
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers,
     subTracks + stages + keyCapabilities + capabilities + products + scenarios + demands + industries + customers + suppliers AS allTags
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers,
     [term IN $strongTerms WHERE any(tag IN allTags WHERE tag IS NOT NULL AND tag CONTAINS term)] AS strongHits,
     [term IN $weakTerms WHERE any(tag IN allTags WHERE tag IS NOT NULL AND tag CONTAINS term)] AS weakHits
WHERE size(strongHits) > 0 OR size(weakHits) > 0
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       keyCapabilities[0..8] AS keyCapabilities,
       capabilities[0..8] AS capabilities,
       products[0..8] AS products,
       customers[0..8] AS customers,
       suppliers[0..8] AS suppliers,
       scenarios[0..8] AS scenarios,
       demands[0..8] AS demands,
       industries[0..8] AS industries,
       strongHits[0..12] AS neo4jStrongHits,
       weakHits[0..8] AS neo4jWeakHits,
       'external_company' AS opportunityType
LIMIT $candidateLimit
"""

GRAPH_FACT_DISCOVERY_ENTERPRISE_CONTEXT = """
MATCH (e:Enterprise)
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, customers, scenarios, industries, demands, suppliers,
     subTracks + stages + keyCapabilities + capabilities + products + customers + scenarios + industries + demands + suppliers AS allTags
WITH e, subTracks, stages, keyCapabilities, capabilities, products, customers, scenarios, industries, demands, suppliers, allTags,
     [term IN $targetTerms WHERE any(tag IN allTags WHERE tag IS NOT NULL AND tag CONTAINS term)] AS targetHits,
     [term IN $evidenceTerms WHERE any(tag IN allTags WHERE tag IS NOT NULL AND tag CONTAINS term)] AS evidenceHits,
     [term IN $excludeTerms WHERE any(tag IN allTags WHERE tag IS NOT NULL AND tag CONTAINS term)] AS excludeHits
WHERE size(targetHits) > 0 OR size(evidenceHits) > 0
RETURN e.name AS targetEnterprise,
       subTracks[0..8] AS subTracks,
       stages[0..8] AS stages,
       keyCapabilities[0..10] AS keyCapabilities,
       capabilities[0..12] AS capabilities,
       products[0..12] AS products,
       customers[0..12] AS customers,
       scenarios[0..12] AS scenarios,
       industries[0..12] AS industries,
       demands[0..8] AS demands,
       suppliers[0..8] AS suppliers,
       targetHits[0..12] AS targetHits,
       evidenceHits[0..12] AS evidenceHits,
       excludeHits[0..8] AS excludeHits,
       'graph_fact_discovery' AS opportunityType
LIMIT $candidateLimit
"""

GRAPH_QA_ENTERPRISE_PROFILE = """
MATCH (e:Enterprise)
WHERE any(term IN $terms WHERE e.name CONTAINS term OR term CONTAINS e.name)
WITH e
ORDER BY size(e.name) DESC
LIMIT $limit
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers,
     subTracks + stages + keyCapabilities + capabilities + products + scenarios + demands + industries + customers + suppliers AS allTags
RETURN e.name AS targetEnterprise,
       subTracks[0..8] AS subTracks,
       stages[0..8] AS stages,
       keyCapabilities[0..10] AS keyCapabilities,
       capabilities[0..10] AS capabilities,
       products[0..10] AS products,
       customers[0..10] AS customers,
       scenarios[0..10] AS scenarios,
       industries[0..10] AS industries,
       demands[0..8] AS demands,
       suppliers[0..8] AS suppliers,
       [term IN $terms WHERE e.name CONTAINS term OR term CONTAINS e.name OR any(tag IN allTags WHERE tag IS NOT NULL AND (tag CONTAINS term OR term CONTAINS tag))][0..12] AS matchedTerms,
       ['企业名称/画像'] AS matchedFields,
       'enterprise_profile' AS evidenceType,
       80 + size([term IN $terms WHERE e.name CONTAINS term OR term CONTAINS e.name]) * 10 AS matchScore
ORDER BY matchScore DESC, targetEnterprise
"""

GRAPH_QA_TAG_RELATED_ENTERPRISES = """
CALL () {
  MATCH (e:Enterprise)
  WHERE any(term IN $terms WHERE e.name CONTAINS term OR term CONTAINS e.name)
  RETURN e, 80 AS baseScore, ['企业名称'] AS baseFields
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[r:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 70 AS baseScore, collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[r:APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 58 AS baseScore, collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[r:FOCUSES_ON_SUB_TRACK|LOCATED_IN_STAGE]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 48 AS baseScore, collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[r:HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 42 AS baseScore, collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
}
WITH e, max(baseScore) AS baseScore, collect(baseFields) AS fieldGroups
ORDER BY baseScore DESC, e.name
LIMIT $candidateLimit
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers, baseScore, fieldGroups,
     subTracks + stages + keyCapabilities + capabilities + products + scenarios + demands + industries + customers + suppliers AS allTags
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers, baseScore, fieldGroups,
     [term IN $terms WHERE e.name CONTAINS term OR term CONTAINS e.name OR any(tag IN allTags WHERE tag IS NOT NULL AND (tag CONTAINS term OR term CONTAINS tag))] AS matchedTerms
WHERE size(matchedTerms) > 0
RETURN e.name AS targetEnterprise,
       subTracks[0..8] AS subTracks,
       stages[0..8] AS stages,
       keyCapabilities[0..10] AS keyCapabilities,
       capabilities[0..10] AS capabilities,
       products[0..10] AS products,
       customers[0..10] AS customers,
       scenarios[0..10] AS scenarios,
       industries[0..10] AS industries,
       demands[0..8] AS demands,
       suppliers[0..8] AS suppliers,
       matchedTerms[0..12] AS matchedTerms,
       reduce(fields = [], group IN fieldGroups | fields + group)[0..8] AS matchedFields,
       'tag_related_enterprise' AS evidenceType,
       baseScore + size(matchedTerms) * 5 AS matchScore
ORDER BY matchScore DESC, size(matchedTerms) DESC, targetEnterprise
LIMIT $limit
"""

GRAPH_QA_COOPERATION_CANDIDATES = """
CALL () {
  MATCH (target:Enterprise)
  WHERE any(term IN $terms WHERE target.name CONTAINS term OR term CONTAINS target.name)
  CALL (target) {
    OPTIONAL MATCH (target)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT|APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|FOCUSES_ON_SUB_TRACK|LOCATED_IN_STAGE|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
    RETURN collect(DISTINCT tag.name)[0..60] AS targetTags
  }
  WITH target, [tag IN targetTags WHERE tag IS NOT NULL] AS targetTags
  MATCH (e:Enterprise)
  WHERE e <> target
    AND EXISTS {
      MATCH (e)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT|APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|FOCUSES_ON_SUB_TRACK|LOCATED_IN_STAGE|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
      WHERE tag.name IS NOT NULL
        AND any(targetTag IN targetTags WHERE tag.name CONTAINS targetTag OR targetTag CONTAINS tag.name)
    }
  RETURN e, 72 AS baseScore, ['目标企业画像相似/互补'] AS baseFields
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[r:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT|APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|FOCUSES_ON_SUB_TRACK|LOCATED_IN_STAGE|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e,
         CASE
           WHEN type(r) IN ['HAS_KEY_CAPABILITY', 'HAS_CAPABILITY', 'PROVIDES_PRODUCT'] THEN 68
           WHEN type(r) IN ['APPLIES_TO_SCENARIO', 'HAS_DEMAND', 'SERVES_INDUSTRY'] THEN 58
           ELSE 48
         END AS baseScore,
         collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
}
WITH e, max(baseScore) AS baseScore, collect(baseFields) AS fieldGroups
ORDER BY baseScore DESC, e.name
LIMIT $candidateLimit
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers, baseScore, fieldGroups,
     subTracks + stages + keyCapabilities + capabilities + products + scenarios + demands + industries + customers + suppliers AS allTags
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers, baseScore, fieldGroups,
     [term IN $terms WHERE e.name CONTAINS term OR term CONTAINS e.name OR any(tag IN allTags WHERE tag IS NOT NULL AND (tag CONTAINS term OR term CONTAINS tag))] AS matchedTerms
RETURN e.name AS targetEnterprise,
       subTracks[0..8] AS subTracks,
       stages[0..8] AS stages,
       keyCapabilities[0..10] AS keyCapabilities,
       capabilities[0..10] AS capabilities,
       products[0..10] AS products,
       customers[0..10] AS customers,
       scenarios[0..10] AS scenarios,
       industries[0..10] AS industries,
       demands[0..8] AS demands,
       suppliers[0..8] AS suppliers,
       matchedTerms[0..12] AS matchedTerms,
       reduce(fields = [], group IN fieldGroups | fields + group)[0..8] AS matchedFields,
       'cooperation_candidate' AS evidenceType,
       baseScore + size(matchedTerms) * 5 AS matchScore
ORDER BY matchScore DESC, size(matchedTerms) DESC, targetEnterprise
LIMIT $limit
"""

GRAPH_QA_CUSTOMER_SUPPLY_EVIDENCE = """
CALL () {
  MATCH (e:Enterprise)-[r:HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 86 AS baseScore, collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[r:APPLIES_TO_SCENARIO|SERVES_INDUSTRY|HAS_DEMAND]->(tag)
  WHERE tag.name IS NOT NULL AND any(term IN $terms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 64 AS baseScore, collect(DISTINCT type(r))[0..4] AS baseFields
  LIMIT $candidateLimit
}
WITH e, max(baseScore) AS baseScore, collect(baseFields) AS fieldGroups
ORDER BY baseScore DESC, e.name
LIMIT $candidateLimit
CALL (e) {
  OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
  RETURN collect(DISTINCT s.name) AS subTracks
}
CALL (e) {
  OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
  RETURN collect(DISTINCT st.name) AS stages
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
  RETURN collect(DISTINCT k.name) AS keyCapabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
  RETURN collect(DISTINCT cap.name) AS capabilities
}
CALL (e) {
  OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
  RETURN collect(DISTINCT product.name) AS products
}
CALL (e) {
  OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
  RETURN collect(DISTINCT scenario.name) AS scenarios
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
  RETURN collect(DISTINCT demand.name) AS demands
}
CALL (e) {
  OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
  RETURN collect(DISTINCT industry.name) AS industries
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
  RETURN collect(DISTINCT customer.name) AS customers
}
CALL (e) {
  OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
  RETURN collect(DISTINCT supplier.name) AS suppliers
}
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers, baseScore, fieldGroups,
     customers + suppliers AS directEvidence,
     subTracks + stages + keyCapabilities + capabilities + products + scenarios + demands + industries + customers + suppliers AS allTags
WITH e, subTracks, stages, keyCapabilities, capabilities, products, scenarios, demands, industries, customers, suppliers, baseScore, fieldGroups,
     [term IN $terms WHERE any(tag IN directEvidence WHERE tag IS NOT NULL AND (tag CONTAINS term OR term CONTAINS tag))] AS directMatchedTerms,
     [term IN $terms WHERE any(tag IN allTags WHERE tag IS NOT NULL AND (tag CONTAINS term OR term CONTAINS tag))] AS allMatchedTerms
RETURN e.name AS targetEnterprise,
       subTracks[0..8] AS subTracks,
       stages[0..8] AS stages,
       keyCapabilities[0..10] AS keyCapabilities,
       capabilities[0..10] AS capabilities,
       products[0..10] AS products,
       customers[0..10] AS customers,
       scenarios[0..10] AS scenarios,
       industries[0..10] AS industries,
       demands[0..8] AS demands,
       suppliers[0..8] AS suppliers,
       (directMatchedTerms + allMatchedTerms)[0..12] AS matchedTerms,
       reduce(fields = [], group IN fieldGroups | fields + group)[0..8] AS matchedFields,
       'customer_supply_evidence' AS evidenceType,
       baseScore + size(directMatchedTerms) * 12 + size(allMatchedTerms) * 4 AS matchScore
ORDER BY matchScore DESC, size(directMatchedTerms) DESC, targetEnterprise
LIMIT $limit
"""

OPPORTUNITIES_TECHNOLOGY_SCOPE = """
CALL () {
  MATCH (e:Enterprise)
  WHERE any(term IN $queryTerms WHERE e.name CONTAINS term)
  RETURN e, 70 AS baseScore
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT]->(tag)
  WHERE tag.name IS NOT NULL
    AND any(term IN $queryTerms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 60 AS baseScore
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[:LOCATED_IN_STAGE|FOCUSES_ON_SUB_TRACK]->(tag)
  WHERE tag.name IS NOT NULL
    AND any(term IN $queryTerms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 45 AS baseScore
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[:APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
  WHERE tag.name IS NOT NULL
    AND any(term IN $queryTerms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 30 AS baseScore
  LIMIT $candidateLimit
}
WITH e, max(baseScore) AS baseScore
ORDER BY baseScore DESC, e.name
LIMIT $candidateLimit
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scenario:Scenario)
OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
WITH e, collect(DISTINCT k.name) AS keyCapabilities, collect(DISTINCT cap.name) AS capabilities,
     collect(DISTINCT product.name) AS products, collect(DISTINCT scenario.name) AS scenarios,
     collect(DISTINCT demand.name) AS demands, collect(DISTINCT st.name) AS stages,
     collect(DISTINCT s.name) AS subTracks, collect(DISTINCT industry.name) AS industries,
     collect(DISTINCT customer.name) AS customers, collect(DISTINCT supplier.name) AS suppliers,
     baseScore
WITH e, subTracks, stages, scenarios, demands, industries, customers, suppliers,
     keyCapabilities + capabilities + products AS targetCapabilities,
     [x IN keyCapabilities + capabilities + products + scenarios + demands + stages + subTracks + industries + customers + suppliers
      WHERE x IS NOT NULL AND any(term IN $queryTerms WHERE x CONTAINS term OR term CONTAINS x)] AS matchedTerms,
     baseScore
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       targetCapabilities[0..8] AS targetCapabilities,
       scenarios[0..5] AS scenarios,
       demands[0..5] AS demands,
       industries[0..5] AS industries,
       customers[0..5] AS customers,
       suppliers[0..5] AS suppliers,
       matchedTerms[0..8] AS matchedTerms,
       'technology_scope' AS opportunityType,
       CASE WHEN baseScore >= 45 OR size(matchedTerms) >= 3 THEN 'high' ELSE 'medium' END AS confidence,
       baseScore + size(matchedTerms) * 5 AS matchScore
ORDER BY matchScore DESC, size(matchedTerms) DESC, e.name
LIMIT $limit
"""

OPPORTUNITIES_INDUSTRY_DIRECTION = """
CALL () {
  MATCH (e:Enterprise)
  WHERE any(term IN $queryTerms WHERE e.name CONTAINS term)
  RETURN e, 70 AS baseScore
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[:HAS_KEY_CAPABILITY|HAS_CAPABILITY|PROVIDES_PRODUCT]->(tag)
  WHERE tag.name IS NOT NULL
    AND any(term IN $queryTerms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 60 AS baseScore
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[:LOCATED_IN_STAGE|FOCUSES_ON_SUB_TRACK]->(tag)
  WHERE tag.name IS NOT NULL
    AND any(term IN $queryTerms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 45 AS baseScore
  LIMIT $candidateLimit
UNION
  MATCH (e:Enterprise)-[:APPLIES_TO_SCENARIO|HAS_DEMAND|SERVES_INDUSTRY|HAS_CUSTOMER|HAS_SUPPLIER]->(tag)
  WHERE tag.name IS NOT NULL
    AND any(term IN $queryTerms WHERE tag.name CONTAINS term OR term CONTAINS tag.name)
  RETURN e, 30 AS baseScore
  LIMIT $candidateLimit
}
WITH e, max(baseScore) AS baseScore
ORDER BY baseScore DESC, e.name
LIMIT $candidateLimit
OPTIONAL MATCH (e)-[:FOCUSES_ON_SUB_TRACK]->(s:SubTrack)
OPTIONAL MATCH (e)-[:LOCATED_IN_STAGE]->(st:ChainStage)
OPTIONAL MATCH (e)-[:HAS_KEY_CAPABILITY]->(k:KeyCapability)
OPTIONAL MATCH (e)-[:HAS_CAPABILITY]->(cap:Capability)
OPTIONAL MATCH (e)-[:PROVIDES_PRODUCT]->(product:Product)
OPTIONAL MATCH (e)-[:APPLIES_TO_SCENARIO]->(scene:Scenario)
OPTIONAL MATCH (e)-[:HAS_DEMAND]->(demand:DemandTag)
OPTIONAL MATCH (e)-[:SERVES_INDUSTRY]->(industry:Industry)
OPTIONAL MATCH (e)-[:HAS_CUSTOMER]->(customer:Customer)
OPTIONAL MATCH (e)-[:HAS_SUPPLIER]->(supplier:Supplier)
OPTIONAL MATCH (scenario:ApplicationScenario)-[:DRIVES_STAGE]->(st)
WITH e, collect(DISTINCT s.name) AS subTracks, collect(DISTINCT st.name) AS stages,
     collect(DISTINCT k.name) AS keyCapabilities, collect(DISTINCT cap.name) AS capabilities,
     collect(DISTINCT product.name) AS products, collect(DISTINCT scene.name) AS profileScenarios,
     collect(DISTINCT demand.name) AS demands, collect(DISTINCT industry.name) AS industries,
     collect(DISTINCT customer.name) AS customers, collect(DISTINCT supplier.name) AS suppliers,
     collect(DISTINCT scenario.name) AS graphScenarios, baseScore
WITH e, subTracks, stages, demands, industries, graphScenarios + profileScenarios AS scenarios, customers, suppliers,
     keyCapabilities + capabilities + products AS targetCapabilities,
     [x IN keyCapabilities + capabilities + products + graphScenarios + profileScenarios + demands + stages + subTracks + industries + customers + suppliers
      WHERE x IS NOT NULL AND any(term IN $queryTerms WHERE x CONTAINS term OR term CONTAINS x)] AS matchedTerms,
     baseScore
RETURN e.name AS targetEnterprise,
       subTracks[0] AS subTrack,
       stages[0] AS targetStage,
       targetCapabilities[0..8] AS targetCapabilities,
       scenarios[0..5] AS scenarios,
       demands[0..5] AS demands,
       industries[0..5] AS industries,
       customers[0..5] AS customers,
       suppliers[0..5] AS suppliers,
       matchedTerms[0..8] AS matchedTerms,
       'industry_direction' AS opportunityType,
       CASE WHEN baseScore >= 45 OR size(matchedTerms) >= 3 THEN 'high' ELSE 'medium' END AS confidence,
       baseScore + size(matchedTerms) * 5 AS matchScore
ORDER BY matchScore DESC, size(matchedTerms) DESC, e.name
LIMIT $limit
"""
