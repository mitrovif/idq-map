"""
Sub-reason taxonomy: the mechanisms that sit underneath each response option.

WHY THIS LAYER EXISTS
The eight response options classify at the level of a CATEGORY OF THREAT. What a
respondent actually experienced is a MECHANISM: a checkpoint where they were asked
their tribe, a bulldozer, a 72-hour ultimatum, three failed rainy seasons. The gap
between those two levels is where measurement error lives - a respondent who does
not recognise their mechanism in an option will answer "none of the above", and a
non-displaced person who recognises theirs too loosely will produce a false positive.

HOW IT WAS BUILT - three inputs, in order of evidential weight
  1. SOURCE VOCABULARIES. Every category the six databases actually use (68 of
     them). These are mechanisms that somebody already counts.
  2. DOCUMENTED QUALITATIVE RESEARCH. Mechanisms named in HRW, Amnesty, OHCHR and
     Crisis Group investigations across the twenty largest displacement contexts.
     These are mechanisms nobody counts but that demonstrably displace people.
  3. RESPONDENT PHRASING. How a person would plainly describe the mechanism, in
     the register a survey answer actually arrives in - not agency vocabulary.

counted:
  yes      at least one database has a category for this mechanism
  partial  captured only indirectly, or only when it turns lethal
  no       no database anywhere counts it; it exists here on qualitative evidence
"""

SUB = {
1: ("Threat of armed conflict or war", [
 ("Front-line fighting reaches the area", "Armed clashes between forces move into or near the settlement.",
  "The fighting reached our village and we ran.", ["IDMC IAC/NIAC","ACLED Armed clash","UCDP state-based"], "yes"),
 ("Aerial bombardment or shelling", "Air strikes, drone strikes, artillery or missile attack on populated areas.",
  "Shells landed on the houses near us.", ["ACLED Air/drone strike","ACLED Shelling"], "yes"),
 ("Explosive remnants, landmines, IEDs", "Land or routes made unusable by mines and unexploded ordnance, often blocking return as much as causing flight.",
  "The road and the fields were mined so we could not stay.", ["ACLED Remote explosive/landmine/IED"], "yes"),
 ("Change of territorial control", "A different armed actor takes over the area; people flee the incoming authority rather than the fighting itself.",
  "The other side took the town, so we left.", ["ACLED Government regains territory","ACLED Non-state actor overtakes territory"], "yes"),
 ("Siege, encirclement, starvation as a method of war", "Movement and supplies cut off until leaving is the only option.",
  "Nothing could get in or out for months.", ["not separately coded"], "partial"),
 ("Forced recruitment or conscription by armed actors", "Families leave to prevent sons or daughters being taken.",
  "They came to take the young men, so we sent them away and then followed.", ["DTM Forced recruitment","HRW on M23"], "partial"),
 ("Anticipatory flight ahead of an advancing front", "Leaving BEFORE violence arrives, on the basis of what happened elsewhere. Invisible to event data by definition - there is no event at the origin.",
  "We left before they arrived because we heard what they did in the next district.", ["none"], "no"),
 ("Home or infrastructure destroyed, making return impossible", "The displacement continues because there is nothing to return to.",
  "Our house was destroyed, so even when it was calm we could not go back.", ["IDMC 'Is housing destruction'"], "partial"),
]),
2: ("Widespread violence or breakdown of public order", [
 ("Communal violence over land, water or grazing", "Violence between communities over resources, frequently seasonal and recurrent.",
  "Two communities started fighting over the wells and the grazing land.", ["IDMC OSV","ACLED Mob violence","UCDP non-state"], "yes"),
 ("Criminal armed groups controlling territory", "Gangs or cartels exercising de facto control, extorting and expelling.",
  "The gang took over our neighbourhood and told families to go.", ["IDMC OSV","ACLED Mob violence"], "partial"),
 ("Riots and mob violence", "Crowd violence targeting people, homes or businesses.",
  "A crowd came through and burned the shops.", ["ACLED Mob violence","ACLED Violent demonstration"], "yes"),
 ("Violent suppression of demonstrations", "State or para-state force used against protesters. Straddles this option and code 4.",
  "They fired on the demonstration and afterwards came looking for people.", ["ACLED Excessive force against protesters"], "yes"),
 ("Cattle or resource raiding", "Armed raids on livestock and stores that strip livelihoods and force movement.",
  "They came for the cattle and burned what was left.", ["IDMC OSV","ACLED"], "partial"),
 ("Kidnapping for ransom", "Abduction as an economic activity, producing pre-emptive flight.",
  "They were taking people from the road for money, so we moved to the town.", ["ACLED Abduction/forced disappearance"], "partial"),
 ("Collapse of policing - no protection available", "Not an event but an absence. Nothing in event data records the non-arrival of police.",
  "There was nobody to stop it and nobody to complain to.", ["none"], "no"),
]),
3: ("Discrimination or persecution", [
 ("Screening by ethnicity, tribe or language at checkpoints", "Identity checked at a barrier and treatment decided by the answer.",
  "At the checkpoint they asked what tribe we were.", ["qualitative: HRW El Geneina, Juba"], "no"),
 ("Collective expulsion ultimatum", "A group given hours or days to leave on the basis of who they are.",
  "They gave all of us of our religion one day to be out of the town.", ["qualitative: HRW Yaloke, Western Tigray"], "no"),
 ("Religious persecution", "Conversion demanded, worship prevented, places of worship destroyed.",
  "They said we had to convert or go, and they burned the church.", ["DTM Religious persecution","V-Dem v2clrelig"], "partial"),
 ("Political persecution", "Targeted for party affiliation, voting, activism or association.",
  "My son worked at the polling table for the opposition, and then they marked our door.", ["V-Dem","UNHCR recognition"], "partial"),
 ("Language or regional identity targeting", "Persecuted for the language spoken or the region of origin, not ethnicity as usually defined.",
  "They called us names because we speak English and said we were all with the fighters.", ["qualitative: HRW Cameroon"], "no"),
 ("Clan, caste or minority-group subordination", "Groups without armed protection dispossessed by stronger ones; ascribed inferior status.",
  "We are from a small group with no gunmen of our own, so a stronger group took our farm.", ["qualitative: HRW/NRC Somalia"], "no"),
 ("Denial or removal of nationality", "Citizenship legally withheld, making a whole population expellable.",
  "They said we do not belong to this country and we have no citizenship card.", ["qualitative: Myanmar 1982 law"], "no"),
 ("Persecution on grounds of sexual orientation or gender identity", "Criminalisation, mob violence, family expulsion, blackmail.",
  "People found out about me and I could not stay in my own family's area.", ["qualitative: Colombia JEP, Afghanistan"], "no"),
 ("Identity documents seized or withheld", "Papers taken so that return, movement or proof of ownership becomes impossible.",
  "They took our identity papers before they let us cross.", ["qualitative: HRW Western Tigray"], "no"),
 ("Targeted on a misattributed identity", "Attacked for an identity the attacker assigned, not one held. A question about the respondent's own group membership can miss this entirely.",
  "They killed anyone carrying a government card - it was the paper, not who we were.", ["qualitative: Crisis Group Mozambique"], "no"),
 ("Discriminatory denial of aid, services or land rights", "Not violence, but exclusion severe enough that staying is untenable.",
  "We were not allowed to register for the food, and could not get work.", ["V-Dem v2clsocgrp"], "partial"),
]),
4: ("Threat of human rights violations by authorities", [
 ("Arbitrary arrest and detention", "Held without charge or trial; families flee before the next round.",
  "They took my brother and he has never been to court.", ["ACLED Arrests","V-Dem"], "partial"),
 ("Torture or ill-treatment in custody", "Released detainees and their families leave.",
  "They beat him for months and when they let him out they kept watching him.", ["V-Dem v2cltort"], "partial"),
 ("Enforced disappearance", "Taken by officials or men in uniform and never accounted for.",
  "Men in uniform came at night and we never saw him again.", ["ACLED Abduction/forced disappearance"], "partial"),
 ("Extrajudicial killing by state forces", "The one part of code 4 that global data does count.",
  "The soldiers shot people in the street during the operation.", ["UCDP one-sided (gov)","V-Dem v2clkill"], "yes"),
 ("Confiscation or destruction of property by authorities", "Named explicitly in the option, and almost entirely uncounted.",
  "They put a seal on the house and said it was taken.", ["V-Dem v2xcl_prpty","qualitative"], "partial"),
 ("Punitive demolition of homes", "Housing destroyed as collective punishment rather than for a project.",
  "They destroyed our part of the neighbourhood because of who lived there.", ["qualitative: HRW Syria"], "no"),
 ("Eviction from a displacement site by authorities", "Being displaced a second time, by the state, from a camp or settlement.",
  "The commissioner came with a bulldozer and destroyed the shelter.", ["qualitative: HRW Somalia, Nigeria"], "no"),
 ("Banishment or denial of return through security screening", "Not why people LEFT but why they cannot go back. The stem 'have you ever left a home due to' misses this.",
  "Because my brother's name was on a list they will not let us back into the neighbourhood.", ["qualitative: HRW Iraq"], "no"),
 ("Forced conscription by the state", "Fleeing the draft or indefinite national service.",
  "He would have been taken for national service with no end, so he left.", ["none"], "no"),
 ("Surveillance and explicit threat by officials", "No arrest, but a credible warning that compels flight.",
  "They told him to stop working and that they were watching him.", ["none"], "no"),
 ("Denial of documentation", "Papers, permits or registration withheld until life becomes unworkable.",
  "They would not give us the papers, so we could not work or travel.", ["qualitative: HRW Western Tigray"], "no"),
 ("Forced return or deportation", "Expelled back across a border. Afghanistan's largest current flow, and NO response option covers it.",
  "We were put on a bus at the border and sent back.", ["none"], "no"),
]),
5: ("Other threats of violence against you", [
 ("Named, addressed personal threat", "A message, a mark on the door, a list. Arrives as a personal threat even when the driver is political.",
  "They put a mark on our door and we understood we had to go.", ["qualitative: OCCRP Venezuela"], "no"),
 ("Sexual and gender-based violence", "Massively under-reported in every source, and straddles codes 3, 4 and 5 depending on perpetrator and motive.",
  "What happened to my daughter meant we could not stay there.", ["ACLED Sexual violence"], "partial"),
 ("Abduction by non-state actors", "Taken by armed or criminal groups rather than authorities.",
  "They took him and we never found out who they were.", ["ACLED Abduction/forced disappearance"], "partial"),
 ("Blood feud or revenge violence", "Inter-family cycles of retaliation that displace whole households.",
  "After the killing, the other family would come for us.", ["none"], "no"),
 ("Accusation of witchcraft or ritual violence", "Documented as a displacement driver in Haiti; likely present elsewhere and invisible.",
  "They said the old people were doing witchcraft and started killing them.", ["qualitative: ACLED Haiti"], "no"),
 ("Domestic or intimate-partner violence", "Whether this belongs in a forced-displacement instrument at all is a live question - but people will report it, so enumerators need a rule.",
  "I left because of my husband.", ["none"], "no"),
]),
6: ("Natural disasters", [
 ("Flood - riverine, flash or coastal", "The single largest disaster mechanism worldwide by people displaced.",
  "The water came into the houses and did not go down.", ["IDMC Flood","DTM Flood"], "yes"),
 ("Storm, cyclone, typhoon, hurricane", "Largest single hazard sub-type in IDMC's data.",
  "The storm took the roof off and the whole area was flattened.", ["IDMC Typhoon/Hurricane/Cyclone"], "yes"),
 ("Drought and failed rains", "Slow-onset. A household that left over three seasons may not describe it as fleeing at all.",
  "The rains failed three times, the animals died, and there was nothing left.", ["IDMC Drought","DTM Drought"], "yes"),
 ("Earthquake", "Sudden, and usually followed by a return question rather than a leaving question.",
  "The house came down in the earthquake.", ["IDMC Earthquake"], "yes"),
 ("Landslide or mass movement", "Often triggered by rain, sometimes by deforestation or quarrying - a code 6/7 boundary case.",
  "The hillside came down onto the houses below.", ["IDMC Landslide/Wet mass movement"], "yes"),
 ("Volcanic activity", "Includes long evacuation periods with no defined return.",
  "The mountain started throwing ash and they moved everybody out.", ["IDMC Volcanic activity"], "yes"),
 ("Coastal erosion and sea-level rise", "The slowest onset of all; displacement is gradual and rarely recorded as an event.",
  "The sea has taken the land where our house was, a little each year.", ["IDMC Erosion, Sea level rise"], "partial"),
 ("Extreme temperature", "Cold waves and heat events; small in the data, real for the households affected.",
  "The cold killed the animals and we could not stay through it.", ["IDMC Cold wave, Extreme temperature"], "yes"),
 ("Pre-emptive evacuation ahead of a hazard", "Left before impact on an official warning. Large in IDMC's flow figures and the most likely mismatch with 'had to flee a home'.",
  "They told us a storm was coming and moved us for a week.", ["IDMC 'Displacement occurred' flag"], "yes"),
]),
7: ("Man-made events", [
 ("Dam construction and reservoir inundation", "Land permanently flooded by a planned reservoir. Merowe 50,000+, Makhoul 100,000+.",
  "They are building a dam and our village will be under the water.", ["qualitative: FMR Sudan, Save the Tigris Iraq"], "no"),
 ("Mining and quarry concessions", "Communities cleared for extraction, sometimes with houses marked for demolition.",
  "The mining company said the land was theirs and put marks on the houses.", ["qualitative: Amnesty DRC, ROAPE Burkina Faso"], "no"),
 ("Urban redevelopment and corridor projects", "'Beautification', modernisation and clearance of informal settlements.",
  "They marked our neighbourhood for the new city project and knocked it down.", ["qualitative: Amnesty Ethiopia, Nigeria"], "no"),
 ("Transport infrastructure - roads, ports, airports, rail", "Route and terminal construction displacing settlements along the line.",
  "They said the village had to go because of the new port.", ["qualitative: Cameroon Kribi, DRC Lobito"], "no"),
 ("Agricultural concession or plantation", "Land allocated to commercial agriculture over existing users.",
  "They took our grazing land along the river for the sugar farm.", ["qualitative: HRW Lower Omo"], "no"),
 ("Industrial pollution or contamination", "Water, soil or air made unusable. Harm is well documented; displacement attribution is thin.",
  "The waste got into the water, the fish and cattle died, and people moved away.", ["qualitative: Amnesty Niger Delta, RVI South Sudan"], "no"),
 ("Oil and gas operations", "Flaring, produced-water discharge and land take around fields.",
  "The gas flare burns beside the houses all night.", ["qualitative: HRW Iraq"], "no"),
 ("Nuclear or industrial accident", "Rare, enormous, permanent. Chornobyl relocated ~350,000 - within a respondent's lifetime.",
  "After the reactor exploded they told us the whole town had to leave and never come back.", ["qualitative: IAEA"], "no"),
 ("Dam release or infrastructure failure", "A structure operating or failing rather than a natural hazard. Counted by IDMC, but filed under Disaster.",
  "They opened the dam and the water came down onto us.", ["IDMC Dam release flood"], "yes"),
 ("Forced eviction from informal settlement", "Land cleared for private development. Somalia: 1.5m people affected 2018-2024.",
  "They came early with tractors and pulled down our shelter to build apartments.", ["qualitative: NRC Somalia"], "no"),
 ("Conservation and protected-area displacement", "Communities removed to create or enforce parks and reserves. Documented globally, counted nowhere.",
  "They made it a park and told us we could no longer live or graze inside.", ["none"], "no"),
 ("Subsidence from extraction", "Ground collapse caused by mining or groundwater withdrawal.",
  "The ground opened up where they had been pumping.", ["IDMC Sinkhole"], "partial"),
]),
8: ("A different threat to you or your family's safety", [
 ("Open text [SPECIFY]", "By design this has no sub-taxonomy. Its content IS the enrichment mechanism: verbatim responses here are the only route by which mechanisms nobody has anticipated enter the classification.",
  "-", ["collect verbatim"], "no"),
]),
}

# Not causes of forced displacement - listed so enumerators can RECOGNISE and
# exclude them. DTM records people giving these, so they will arrive in the field.
NOT_FORCED = [
 ("Economic opportunity", "Moved for work, wages or business.", "There was no work at home so I came to the city."),
 ("Lack of services", "Moved for schools, clinics, water or electricity.", "There is no secondary school in our village."),
 ("Family reunification", "Moved to join relatives.", "I came to live with my brother."),
 ("Marriage or household formation", "Customary relocation on marriage.", "I moved to my husband's village."),
 ("Planned resettlement, consented and compensated", "A move people agreed to on adequate terms - distinguishable from code 7 only by consent and compensation.",
  "They offered us new land and we agreed to it."),
]
