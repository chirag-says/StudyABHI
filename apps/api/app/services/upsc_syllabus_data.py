"""
UPSC Syllabus Seed Data
Complete syllabus structure based on official UPSC guidelines.
"""
from typing import Dict, List, Any

# UPSC CSE Syllabus Structure
UPSC_SYLLABUS = {
    "exam_type": {
        "code": "upsc_cse",
        "name": "UPSC Civil Services Examination",
        "description": "Union Public Service Commission Civil Services Examination for IAS, IPS, IFS and other central services."
    },
    "stages": [
        {
            "code": "prelims",
            "name": "Preliminary Examination",
            "description": "Objective type screening test consisting of two papers.",
            "papers": [
                {
                    "code": "gs1_prelims",
                    "name": "General Studies Paper I",
                    "max_marks": 200,
                    "duration_minutes": 120,
                    "is_qualifying": False,
                    "subjects": [
                        {
                            "code": "history",
                            "name": "History of India and Indian National Movement",
                            "weightage": 15,
                            "topics": [
                                {
                                    "code": "ancient-india",
                                    "name": "Ancient India",
                                    "importance": "high",
                                    "estimated_hours": 25,
                                    "subtopics": [
                                        {"code": "indus-valley", "name": "Indus Valley Civilization", "estimated_hours": 4},
                                        {"code": "vedic-period", "name": "Vedic Period", "estimated_hours": 4},
                                        {"code": "jainism-buddhism", "name": "Jainism and Buddhism", "estimated_hours": 5},
                                        {"code": "mauryan-empire", "name": "Mauryan Empire", "estimated_hours": 4},
                                        {"code": "post-mauryan", "name": "Post-Mauryan Period", "estimated_hours": 3},
                                        {"code": "gupta-period", "name": "Gupta Period", "estimated_hours": 3},
                                        {"code": "south-indian-dynasties", "name": "South Indian Dynasties", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "medieval-india",
                                    "name": "Medieval India",
                                    "importance": "high",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "delhi-sultanate", "name": "Delhi Sultanate", "estimated_hours": 5},
                                        {"code": "vijayanagar-bahmani", "name": "Vijayanagar and Bahmani Kingdoms", "estimated_hours": 3},
                                        {"code": "mughal-empire", "name": "Mughal Empire", "estimated_hours": 6},
                                        {"code": "maratha-sikhs", "name": "Marathas and Sikhs", "estimated_hours": 3},
                                        {"code": "bhakti-sufi", "name": "Bhakti and Sufi Movements", "estimated_hours": 3}
                                    ]
                                },
                                {
                                    "code": "modern-india",
                                    "name": "Modern India",
                                    "importance": "critical",
                                    "estimated_hours": 40,
                                    "subtopics": [
                                        {"code": "british-expansion", "name": "British Expansion in India", "estimated_hours": 5},
                                        {"code": "economic-impact", "name": "Economic Impact of British Rule", "estimated_hours": 4},
                                        {"code": "social-reform", "name": "Social and Religious Reform Movements", "estimated_hours": 5},
                                        {"code": "revolt-1857", "name": "Revolt of 1857", "estimated_hours": 4},
                                        {"code": "indian-national-congress", "name": "Indian National Congress", "estimated_hours": 5},
                                        {"code": "gandhian-era", "name": "Gandhian Era", "estimated_hours": 8},
                                        {"code": "revolutionary-movements", "name": "Revolutionary Movements", "estimated_hours": 4},
                                        {"code": "constitutional-development", "name": "Constitutional Development", "estimated_hours": 3},
                                        {"code": "post-independence", "name": "Post-Independence Consolidation", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "art-culture",
                                    "name": "Art and Culture",
                                    "importance": "high",
                                    "estimated_hours": 25,
                                    "subtopics": [
                                        {"code": "indian-architecture", "name": "Indian Architecture", "estimated_hours": 5},
                                        {"code": "paintings-sculptures", "name": "Paintings and Sculptures", "estimated_hours": 4},
                                        {"code": "classical-dance", "name": "Classical Dance Forms", "estimated_hours": 3},
                                        {"code": "classical-music", "name": "Classical Music", "estimated_hours": 3},
                                        {"code": "folk-traditions", "name": "Folk Arts and Traditions", "estimated_hours": 3},
                                        {"code": "literature", "name": "Indian Literature", "estimated_hours": 3},
                                        {"code": "religious-philosophies", "name": "Religious Philosophies", "estimated_hours": 4}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "geography",
                            "name": "Indian and World Geography",
                            "weightage": 15,
                            "topics": [
                                {
                                    "code": "physical-geography",
                                    "name": "Physical Geography",
                                    "importance": "high",
                                    "estimated_hours": 30,
                                    "subtopics": [
                                        {"code": "geomorphology", "name": "Geomorphology", "estimated_hours": 5},
                                        {"code": "climatology", "name": "Climatology", "estimated_hours": 5},
                                        {"code": "oceanography", "name": "Oceanography", "estimated_hours": 4},
                                        {"code": "biogeography", "name": "Biogeography", "estimated_hours": 3},
                                        {"code": "soils", "name": "Soils", "estimated_hours": 3},
                                        {"code": "natural-hazards", "name": "Natural Hazards and Disasters", "estimated_hours": 5},
                                        {"code": "maps", "name": "Maps and Cartography", "estimated_hours": 5}
                                    ]
                                },
                                {
                                    "code": "indian-geography",
                                    "name": "Indian Geography",
                                    "importance": "critical",
                                    "estimated_hours": 35,
                                    "subtopics": [
                                        {"code": "physiography", "name": "Physiography of India", "estimated_hours": 5},
                                        {"code": "drainage-system", "name": "Drainage System", "estimated_hours": 5},
                                        {"code": "indian-climate", "name": "Climate of India", "estimated_hours": 5},
                                        {"code": "vegetation", "name": "Natural Vegetation", "estimated_hours": 3},
                                        {"code": "minerals-energy", "name": "Minerals and Energy Resources", "estimated_hours": 5},
                                        {"code": "agriculture", "name": "Agriculture", "estimated_hours": 6},
                                        {"code": "industries", "name": "Industries", "estimated_hours": 4},
                                        {"code": "transport", "name": "Transport and Communication", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "human-geography",
                                    "name": "Human Geography",
                                    "importance": "medium",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "population", "name": "Population Geography", "estimated_hours": 4},
                                        {"code": "migration", "name": "Migration", "estimated_hours": 2},
                                        {"code": "urbanization", "name": "Urbanization", "estimated_hours": 3},
                                        {"code": "regional-planning", "name": "Regional Planning", "estimated_hours": 3},
                                        {"code": "economic-geography", "name": "Economic Geography", "estimated_hours": 3}
                                    ]
                                },
                                {
                                    "code": "world-geography",
                                    "name": "World Geography",
                                    "importance": "medium",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "continents", "name": "Continents and Countries", "estimated_hours": 5},
                                        {"code": "global-distribution", "name": "Global Distribution of Resources", "estimated_hours": 5},
                                        {"code": "geographical-features", "name": "Major Geographical Features", "estimated_hours": 5}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "polity",
                            "name": "Indian Polity and Governance",
                            "weightage": 18,
                            "topics": [
                                {
                                    "code": "constitution-basics",
                                    "name": "Constitution: Historical Background and Features",
                                    "importance": "critical",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "making-of-constitution", "name": "Making of the Constitution", "estimated_hours": 4},
                                        {"code": "preamble", "name": "Preamble", "estimated_hours": 3},
                                        {"code": "salient-features", "name": "Salient Features of Constitution", "estimated_hours": 5},
                                        {"code": "sources", "name": "Sources of Indian Constitution", "estimated_hours": 3},
                                        {"code": "schedules", "name": "Schedules of the Constitution", "estimated_hours": 5}
                                    ]
                                },
                                {
                                    "code": "fundamental-rights",
                                    "name": "Fundamental Rights",
                                    "importance": "critical",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "right-to-equality", "name": "Right to Equality (Art. 14-18)", "estimated_hours": 3},
                                        {"code": "right-to-freedom", "name": "Right to Freedom (Art. 19-22)", "estimated_hours": 4},
                                        {"code": "right-against-exploitation", "name": "Right Against Exploitation (Art. 23-24)", "estimated_hours": 2},
                                        {"code": "right-to-religion", "name": "Right to Religion (Art. 25-28)", "estimated_hours": 2},
                                        {"code": "cultural-educational", "name": "Cultural and Educational Rights (Art. 29-30)", "estimated_hours": 2},
                                        {"code": "constitutional-remedies", "name": "Constitutional Remedies (Art. 32-35)", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "dpsp-duties",
                                    "name": "DPSP and Fundamental Duties",
                                    "importance": "high",
                                    "estimated_hours": 8,
                                    "subtopics": [
                                        {"code": "dpsp", "name": "Directive Principles of State Policy", "estimated_hours": 5},
                                        {"code": "fundamental-duties", "name": "Fundamental Duties", "estimated_hours": 3}
                                    ]
                                },
                                {
                                    "code": "union-executive",
                                    "name": "Union Executive",
                                    "importance": "critical",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "president", "name": "President of India", "estimated_hours": 5},
                                        {"code": "vice-president", "name": "Vice President", "estimated_hours": 2},
                                        {"code": "prime-minister", "name": "Prime Minister and Council of Ministers", "estimated_hours": 4},
                                        {"code": "cabinet-committees", "name": "Cabinet Committees", "estimated_hours": 2},
                                        {"code": "attorney-general", "name": "Attorney General", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "parliament",
                                    "name": "Parliament",
                                    "importance": "critical",
                                    "estimated_hours": 18,
                                    "subtopics": [
                                        {"code": "lok-sabha", "name": "Lok Sabha", "estimated_hours": 4},
                                        {"code": "rajya-sabha", "name": "Rajya Sabha", "estimated_hours": 4},
                                        {"code": "parliamentary-procedures", "name": "Parliamentary Procedures", "estimated_hours": 4},
                                        {"code": "parliamentary-committees", "name": "Parliamentary Committees", "estimated_hours": 4},
                                        {"code": "legislative-process", "name": "Legislative Process", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "judiciary",
                                    "name": "Judiciary",
                                    "importance": "critical",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "supreme-court", "name": "Supreme Court", "estimated_hours": 5},
                                        {"code": "high-courts", "name": "High Courts", "estimated_hours": 3},
                                        {"code": "subordinate-courts", "name": "Subordinate Courts", "estimated_hours": 2},
                                        {"code": "judicial-review", "name": "Judicial Review", "estimated_hours": 3},
                                        {"code": "pil", "name": "Public Interest Litigation", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "state-government",
                                    "name": "State Government",
                                    "importance": "high",
                                    "estimated_hours": 12,
                                    "subtopics": [
                                        {"code": "governor", "name": "Governor", "estimated_hours": 3},
                                        {"code": "chief-minister", "name": "Chief Minister and Council of Ministers", "estimated_hours": 3},
                                        {"code": "state-legislature", "name": "State Legislature", "estimated_hours": 4},
                                        {"code": "centre-state-relations", "name": "Centre-State Relations", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "local-government",
                                    "name": "Local Government",
                                    "importance": "high",
                                    "estimated_hours": 10,
                                    "subtopics": [
                                        {"code": "panchayati-raj", "name": "Panchayati Raj", "estimated_hours": 5},
                                        {"code": "municipalities", "name": "Municipalities", "estimated_hours": 3},
                                        {"code": "73rd-74th-amendments", "name": "73rd and 74th Amendments", "estimated_hours": 2}
                                    ]
                                },
                                {
                                    "code": "constitutional-bodies",
                                    "name": "Constitutional Bodies",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "election-commission", "name": "Election Commission", "estimated_hours": 3},
                                        {"code": "upsc", "name": "UPSC", "estimated_hours": 2},
                                        {"code": "finance-commission", "name": "Finance Commission", "estimated_hours": 3},
                                        {"code": "cag", "name": "CAG", "estimated_hours": 2},
                                        {"code": "national-commissions", "name": "National Commissions (SC/ST/Women/Minorities)", "estimated_hours": 5}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "economy",
                            "name": "Economic and Social Development",
                            "weightage": 15,
                            "topics": [
                                {
                                    "code": "economic-development",
                                    "name": "Economic Development",
                                    "importance": "critical",
                                    "estimated_hours": 25,
                                    "subtopics": [
                                        {"code": "national-income", "name": "National Income and GDP", "estimated_hours": 4},
                                        {"code": "planning", "name": "Planning and NITI Aayog", "estimated_hours": 4},
                                        {"code": "poverty-unemployment", "name": "Poverty and Unemployment", "estimated_hours": 4},
                                        {"code": "inflation", "name": "Inflation", "estimated_hours": 3},
                                        {"code": "economic-reforms", "name": "Economic Reforms since 1991", "estimated_hours": 5},
                                        {"code": "inclusive-growth", "name": "Inclusive Growth and Development", "estimated_hours": 5}
                                    ]
                                },
                                {
                                    "code": "sectors",
                                    "name": "Sectors of Indian Economy",
                                    "importance": "high",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "agriculture-sector", "name": "Agriculture Sector", "estimated_hours": 6},
                                        {"code": "industry-sector", "name": "Industry Sector", "estimated_hours": 5},
                                        {"code": "services-sector", "name": "Services Sector", "estimated_hours": 4},
                                        {"code": "infrastructure", "name": "Infrastructure", "estimated_hours": 5}
                                    ]
                                },
                                {
                                    "code": "money-banking",
                                    "name": "Money and Banking",
                                    "importance": "critical",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "rbi", "name": "Reserve Bank of India", "estimated_hours": 5},
                                        {"code": "monetary-policy", "name": "Monetary Policy", "estimated_hours": 4},
                                        {"code": "banking-system", "name": "Banking System in India", "estimated_hours": 4},
                                        {"code": "financial-markets", "name": "Financial Markets", "estimated_hours": 3},
                                        {"code": "financial-inclusion", "name": "Financial Inclusion", "estimated_hours": 4}
                                    ]
                                },
                                {
                                    "code": "fiscal-policy",
                                    "name": "Fiscal Policy",
                                    "importance": "critical",
                                    "estimated_hours": 18,
                                    "subtopics": [
                                        {"code": "budget", "name": "Budget and Budgetary Process", "estimated_hours": 5},
                                        {"code": "taxation", "name": "Taxation System", "estimated_hours": 5},
                                        {"code": "gst", "name": "GST", "estimated_hours": 4},
                                        {"code": "fiscal-deficit", "name": "Fiscal Deficit and Public Debt", "estimated_hours": 4}
                                    ]
                                },
                                {
                                    "code": "external-sector",
                                    "name": "External Sector",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "foreign-trade", "name": "Foreign Trade", "estimated_hours": 4},
                                        {"code": "bop", "name": "Balance of Payments", "estimated_hours": 4},
                                        {"code": "exchange-rate", "name": "Exchange Rate", "estimated_hours": 3},
                                        {"code": "fdi-fii", "name": "FDI and FII", "estimated_hours": 4}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "science",
                            "name": "General Science",
                            "weightage": 10,
                            "topics": [
                                {
                                    "code": "physics-chemistry",
                                    "name": "Basic Physics and Chemistry",
                                    "importance": "medium",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "mechanics", "name": "Mechanics and Motion", "estimated_hours": 3},
                                        {"code": "energy", "name": "Energy and Its Forms", "estimated_hours": 3},
                                        {"code": "atomic-structure", "name": "Atomic Structure", "estimated_hours": 3},
                                        {"code": "chemical-reactions", "name": "Chemical Reactions", "estimated_hours": 3},
                                        {"code": "everyday-chemistry", "name": "Everyday Chemistry", "estimated_hours": 3}
                                    ]
                                },
                                {
                                    "code": "biology",
                                    "name": "Biology",
                                    "importance": "high",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "cell-biology", "name": "Cell Biology", "estimated_hours": 4},
                                        {"code": "human-body", "name": "Human Body Systems", "estimated_hours": 5},
                                        {"code": "diseases", "name": "Diseases and Health", "estimated_hours": 5},
                                        {"code": "genetics", "name": "Genetics and Evolution", "estimated_hours": 3},
                                        {"code": "plant-biology", "name": "Plant Biology", "estimated_hours": 3}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "science-tech",
                            "name": "Science and Technology",
                            "weightage": 10,
                            "topics": [
                                {
                                    "code": "technology-development",
                                    "name": "Technology Development in India",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "space-tech", "name": "Space Technology (ISRO)", "estimated_hours": 5},
                                        {"code": "nuclear-tech", "name": "Nuclear Technology", "estimated_hours": 3},
                                        {"code": "defense-tech", "name": "Defense Technology", "estimated_hours": 4},
                                        {"code": "it-development", "name": "IT Development", "estimated_hours": 3}
                                    ]
                                },
                                {
                                    "code": "emerging-tech",
                                    "name": "Emerging Technologies",
                                    "importance": "high",
                                    "estimated_hours": 18,
                                    "subtopics": [
                                        {"code": "ai-ml", "name": "Artificial Intelligence and Machine Learning", "estimated_hours": 4},
                                        {"code": "biotechnology", "name": "Biotechnology", "estimated_hours": 4},
                                        {"code": "nanotechnology", "name": "Nanotechnology", "estimated_hours": 3},
                                        {"code": "blockchain", "name": "Blockchain and Cryptocurrency", "estimated_hours": 3},
                                        {"code": "cyber-security", "name": "Cyber Security", "estimated_hours": 4}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "environment",
                            "name": "Environment and Ecology",
                            "weightage": 10,
                            "topics": [
                                {
                                    "code": "ecology-basics",
                                    "name": "Ecology Basics",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "ecosystems", "name": "Ecosystems", "estimated_hours": 4},
                                        {"code": "food-chain", "name": "Food Chain and Food Web", "estimated_hours": 2},
                                        {"code": "biogeochemical", "name": "Biogeochemical Cycles", "estimated_hours": 3},
                                        {"code": "succession", "name": "Ecological Succession", "estimated_hours": 2},
                                        {"code": "biomes", "name": "Biomes", "estimated_hours": 4}
                                    ]
                                },
                                {
                                    "code": "biodiversity",
                                    "name": "Biodiversity",
                                    "importance": "critical",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "biodiversity-types", "name": "Types of Biodiversity", "estimated_hours": 3},
                                        {"code": "biodiversity-hotspots", "name": "Biodiversity Hotspots", "estimated_hours": 4},
                                        {"code": "protected-areas", "name": "Protected Areas", "estimated_hours": 5},
                                        {"code": "wildlife-conservation", "name": "Wildlife Conservation", "estimated_hours": 4},
                                        {"code": "iucn-red-list", "name": "IUCN Red List", "estimated_hours": 4}
                                    ]
                                },
                                {
                                    "code": "environmental-issues",
                                    "name": "Environmental Issues",
                                    "importance": "critical",
                                    "estimated_hours": 25,
                                    "subtopics": [
                                        {"code": "climate-change", "name": "Climate Change", "estimated_hours": 6},
                                        {"code": "pollution", "name": "Types of Pollution", "estimated_hours": 5},
                                        {"code": "waste-management", "name": "Waste Management", "estimated_hours": 4},
                                        {"code": "desertification", "name": "Desertification and Land Degradation", "estimated_hours": 3},
                                        {"code": "water-crisis", "name": "Water Crisis", "estimated_hours": 4},
                                        {"code": "sustainable-development", "name": "Sustainable Development", "estimated_hours": 3}
                                    ]
                                },
                                {
                                    "code": "environmental-laws",
                                    "name": "Environmental Laws and Policies",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "eia", "name": "Environmental Impact Assessment", "estimated_hours": 3},
                                        {"code": "acts-policies", "name": "Environmental Acts and Policies", "estimated_hours": 5},
                                        {"code": "international-conventions", "name": "International Environmental Conventions", "estimated_hours": 5},
                                        {"code": "ngt", "name": "National Green Tribunal", "estimated_hours": 2}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "current-affairs",
                            "name": "Current Events",
                            "weightage": 7,
                            "topics": [
                                {
                                    "code": "national-importance",
                                    "name": "National Events of Importance",
                                    "importance": "critical",
                                    "estimated_hours": 0,  # Ongoing
                                    "subtopics": []
                                },
                                {
                                    "code": "international-importance",
                                    "name": "International Events of Importance",
                                    "importance": "critical",
                                    "estimated_hours": 0,
                                    "subtopics": []
                                }
                            ]
                        }
                    ]
                },
                {
                    "code": "csat",
                    "name": "General Studies Paper II (CSAT)",
                    "max_marks": 200,
                    "duration_minutes": 120,
                    "is_qualifying": True,
                    "passing_marks": 66,
                    "subjects": [
                        {
                            "code": "comprehension",
                            "name": "Comprehension",
                            "weightage": 30,
                            "topics": [
                                {
                                    "code": "reading-comprehension",
                                    "name": "Reading Comprehension",
                                    "importance": "critical",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "passage-analysis", "name": "Passage Analysis", "estimated_hours": 10},
                                        {"code": "inference", "name": "Drawing Inferences", "estimated_hours": 5},
                                        {"code": "vocabulary", "name": "Vocabulary in Context", "estimated_hours": 5}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "logical-reasoning",
                            "name": "Logical Reasoning and Analytical Ability",
                            "weightage": 35,
                            "topics": [
                                {
                                    "code": "verbal-reasoning",
                                    "name": "Verbal Reasoning",
                                    "importance": "high",
                                    "estimated_hours": 20,
                                    "subtopics": [
                                        {"code": "syllogisms", "name": "Syllogisms", "estimated_hours": 5},
                                        {"code": "statements-arguments", "name": "Statements and Arguments", "estimated_hours": 5},
                                        {"code": "statements-assumptions", "name": "Statements and Assumptions", "estimated_hours": 5},
                                        {"code": "statements-conclusions", "name": "Statements and Conclusions", "estimated_hours": 5}
                                    ]
                                },
                                {
                                    "code": "non-verbal-reasoning",
                                    "name": "Non-Verbal Reasoning",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "series", "name": "Series (Number, Letter, Image)", "estimated_hours": 5},
                                        {"code": "coding-decoding", "name": "Coding-Decoding", "estimated_hours": 5},
                                        {"code": "puzzles", "name": "Puzzles and Arrangements", "estimated_hours": 5}
                                    ]
                                },
                                {
                                    "code": "analytical-ability",
                                    "name": "Analytical Ability",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "data-sufficiency", "name": "Data Sufficiency", "estimated_hours": 5},
                                        {"code": "blood-relations", "name": "Blood Relations", "estimated_hours": 3},
                                        {"code": "direction-sense", "name": "Direction Sense", "estimated_hours": 3},
                                        {"code": "ranking", "name": "Ranking and Order", "estimated_hours": 4}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "basic-numeracy",
                            "name": "Basic Numeracy",
                            "weightage": 25,
                            "topics": [
                                {
                                    "code": "quantitative-aptitude",
                                    "name": "Quantitative Aptitude",
                                    "importance": "high",
                                    "estimated_hours": 30,
                                    "subtopics": [
                                        {"code": "number-system", "name": "Number System", "estimated_hours": 5},
                                        {"code": "percentages", "name": "Percentages", "estimated_hours": 4},
                                        {"code": "averages", "name": "Averages", "estimated_hours": 3},
                                        {"code": "ratio-proportion", "name": "Ratio and Proportion", "estimated_hours": 4},
                                        {"code": "profit-loss", "name": "Profit and Loss", "estimated_hours": 3},
                                        {"code": "time-work", "name": "Time and Work", "estimated_hours": 4},
                                        {"code": "time-distance", "name": "Time and Distance", "estimated_hours": 4},
                                        {"code": "simple-compound-interest", "name": "Simple and Compound Interest", "estimated_hours": 3}
                                    ]
                                }
                            ]
                        },
                        {
                            "code": "data-interpretation",
                            "name": "Data Interpretation",
                            "weightage": 10,
                            "topics": [
                                {
                                    "code": "data-analysis",
                                    "name": "Data Analysis",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": [
                                        {"code": "tables", "name": "Tables", "estimated_hours": 3},
                                        {"code": "bar-charts", "name": "Bar Charts", "estimated_hours": 3},
                                        {"code": "pie-charts", "name": "Pie Charts", "estimated_hours": 3},
                                        {"code": "line-graphs", "name": "Line Graphs", "estimated_hours": 3},
                                        {"code": "mixed-diagrams", "name": "Mixed Diagrams", "estimated_hours": 3}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "code": "mains",
            "name": "Main Examination",
            "description": "Descriptive examination to assess candidates' academic talent and depth of study.",
            "papers": [
                {
                    "code": "essay",
                    "name": "Essay",
                    "max_marks": 250,
                    "duration_minutes": 180,
                    "is_qualifying": False,
                    "subjects": [
                        {
                            "code": "essay-writing",
                            "name": "Essay Writing",
                            "weightage": 100,
                            "topics": [
                                {
                                    "code": "philosophical",
                                    "name": "Philosophical Essays",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": []
                                },
                                {
                                    "code": "socio-economic",
                                    "name": "Socio-Economic Essays",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": []
                                },
                                {
                                    "code": "governance",
                                    "name": "Governance Related Essays",
                                    "importance": "high",
                                    "estimated_hours": 15,
                                    "subtopics": []
                                }
                            ]
                        }
                    ]
                },
                {
                    "code": "gs1_mains",
                    "name": "General Studies I (Indian Heritage, Culture, History, Geography)",
                    "max_marks": 250,
                    "duration_minutes": 180,
                    "is_qualifying": False,
                    "subjects": [
                        {
                            "code": "culture-mains",
                            "name": "Indian Culture",
                            "weightage": 25,
                            "topics": []
                        },
                        {
                            "code": "history-mains",
                            "name": "Modern Indian History",
                            "weightage": 25,
                            "topics": []
                        },
                        {
                            "code": "world-history",
                            "name": "World History",
                            "weightage": 20,
                            "topics": []
                        },
                        {
                            "code": "society",
                            "name": "Indian Society",
                            "weightage": 15,
                            "topics": []
                        },
                        {
                            "code": "geography-mains",
                            "name": "Geography (Physical and Human)",
                            "weightage": 15,
                            "topics": []
                        }
                    ]
                },
                {
                    "code": "gs2_mains",
                    "name": "General Studies II (Governance, Constitution, Polity, IR)",
                    "max_marks": 250,
                    "duration_minutes": 180,
                    "is_qualifying": False,
                    "subjects": [
                        {
                            "code": "constitution-mains",
                            "name": "Indian Constitution and Governance",
                            "weightage": 35,
                            "topics": []
                        },
                        {
                            "code": "social-justice",
                            "name": "Social Justice",
                            "weightage": 20,
                            "topics": []
                        },
                        {
                            "code": "international-relations",
                            "name": "International Relations",
                            "weightage": 25,
                            "topics": []
                        },
                        {
                            "code": "governance-mains",
                            "name": "Governance and Administration",
                            "weightage": 20,
                            "topics": []
                        }
                    ]
                },
                {
                    "code": "gs3_mains",
                    "name": "General Studies III (Technology, Economy, Environment, Security)",
                    "max_marks": 250,
                    "duration_minutes": 180,
                    "is_qualifying": False,
                    "subjects": [
                        {
                            "code": "economy-mains",
                            "name": "Indian Economy",
                            "weightage": 25,
                            "topics": []
                        },
                        {
                            "code": "science-tech-mains",
                            "name": "Science and Technology",
                            "weightage": 20,
                            "topics": []
                        },
                        {
                            "code": "environment-mains",
                            "name": "Environment and Biodiversity",
                            "weightage": 20,
                            "topics": []
                        },
                        {
                            "code": "disaster-management",
                            "name": "Disaster Management",
                            "weightage": 10,
                            "topics": []
                        },
                        {
                            "code": "internal-security",
                            "name": "Internal Security",
                            "weightage": 25,
                            "topics": []
                        }
                    ]
                },
                {
                    "code": "gs4_mains",
                    "name": "General Studies IV (Ethics, Integrity, Aptitude)",
                    "max_marks": 250,
                    "duration_minutes": 180,
                    "is_qualifying": False,
                    "subjects": [
                        {
                            "code": "ethics",
                            "name": "Ethics and Human Interface",
                            "weightage": 40,
                            "topics": []
                        },
                        {
                            "code": "aptitude-mains",
                            "name": "Aptitude and Foundational Values",
                            "weightage": 30,
                            "topics": []
                        },
                        {
                            "code": "case-studies",
                            "name": "Case Studies",
                            "weightage": 30,
                            "topics": []
                        }
                    ]
                }
            ]
        }
    ]
}

# Recommended Study Resources
RECOMMENDED_BOOKS = {
    "polity": [
        {"name": "Indian Polity", "author": "M. Laxmikanth", "type": "primary"},
        {"name": "Introduction to the Constitution of India", "author": "D.D. Basu", "type": "reference"}
    ],
    "history": [
        {"name": "India's Struggle for Independence", "author": "Bipan Chandra", "type": "primary"},
        {"name": "India After Independence", "author": "Bipan Chandra", "type": "primary"},
        {"name": "A Brief History of Modern India", "author": "Spectrum", "type": "primary"}
    ],
    "geography": [
        {"name": "Certificate Physical and Human Geography", "author": "G.C. Leong", "type": "primary"},
        {"name": "Indian Geography", "author": "Majid Husain", "type": "primary"}
    ],
    "economy": [
        {"name": "Indian Economy", "author": "Ramesh Singh", "type": "primary"},
        {"name": "Economic Survey", "author": "Government of India", "type": "reference"}
    ],
    "science": [
        {"name": "Science and Technology", "author": "Ravi Agrahari", "type": "primary"}
    ],
    "environment": [
        {"name": "Environment and Ecology", "author": "P.D. Sharma", "type": "primary"},
        {"name": "Shankar IAS Environment", "author": "Shankar IAS", "type": "primary"}
    ],
    "art-culture": [
        {"name": "Indian Art and Culture", "author": "Nitin Singhania", "type": "primary"}
    ]
}

# Study Plan Phases
STUDY_PHASES = [
    {
        "name": "Foundation Building",
        "description": "Build strong basics by reading NCERTs and foundational books",
        "duration_weeks": 12,
        "focus": ["polity", "history", "geography", "economy"],
        "activities": ["NCERT reading", "Basic books", "Note making"]
    },
    {
        "name": "Prelims Preparation",
        "description": "Cover entire prelims syllabus with focus on MCQ practice",
        "duration_weeks": 16,
        "focus": ["all_subjects"],
        "activities": ["Standard books", "PYQs", "Mock tests", "Current affairs"]
    },
    {
        "name": "Mains Preparation",
        "description": "Deep dive into mains syllabus with answer writing practice",
        "duration_weeks": 20,
        "focus": ["mains_papers"],
        "activities": ["Answer writing", "Essay practice", "Current affairs analysis"]
    },
    {
        "name": "Revision and Mock Tests",
        "description": "Intensive revision and full-length mock tests",
        "duration_weeks": 8,
        "focus": ["revision", "mock_tests"],
        "activities": ["Full revision", "Mock tests", "Previous year analysis"]
    }
]


def get_total_syllabus_hours() -> int:
    """Calculate total study hours required"""
    total = 0
    for stage in UPSC_SYLLABUS["stages"]:
        for paper in stage["papers"]:
            for subject in paper["subjects"]:
                for topic in subject.get("topics", []):
                    total += topic.get("estimated_hours", 0)
                    for subtopic in topic.get("subtopics", []):
                        total += subtopic.get("estimated_hours", 0)
    return total


def get_subjects_list() -> List[Dict]:
    """Get flat list of all subjects"""
    subjects = []
    for stage in UPSC_SYLLABUS["stages"]:
        for paper in stage["papers"]:
            for subject in paper["subjects"]:
                subjects.append({
                    "code": subject["code"],
                    "name": subject["name"],
                    "stage": stage["code"],
                    "paper": paper["code"],
                    "weightage": subject.get("weightage", 0)
                })
    return subjects
