# ADR 0004 — Crop cycles and metric scope

Status: implemented bounded domain contract.

Each logical planting opens a cycle. The first eligible harvest in [planting,next planting) closes; ties use harvest time/system/event ID. No harvest plus next planting is superseded, otherwise open. Distinct simultaneous plantings are ambiguous and fail validation. All trusted harvests reconcile as closing/additional/no eligible prior planting, remaining in event/daily facts. Cycle ID hashes an unambiguous structural tuple.

Yield is first harvest kg / whole-field area at planting. It is not total multi-harvest production or yield over actual planted area. Duration is fractional planting-to-first-harvest days, NULL without harvest. Field chronology alone does not prove a source harvest belonged to a biological crop; explicit source cycle/zone/planted-area contracts are needed before extending the rule.

Daily dates are UTC, flags indicate presence, no calendar spine exists. Irrigation quantities are reported depth sums without area weighting; practices are latest reported flags without historical/as-of validity inference. These limits remain explicit rather than inventing extra measurements.
