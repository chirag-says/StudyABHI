# UPSC Platform User Test Scenarios

## Overview

Three realistic user personas with expected behaviors, AI responses, and roadmap changes.

---

## 👤 Persona 1: Beginner User (Priya)

### Profile
- **Age:** 23
- **Background:** Fresh graduate, first UPSC attempt
- **Tech comfort:** Moderate
- **Study materials:** Downloaded NCERTs, no notes
- **Time available:** 6-8 hours/day
- **Motivation:** High but anxious

### Test Scenario 1.1: First Day Onboarding

**User Actions:**
1. Signs up with email
2. Uploads first PDF (NCERT Polity, 15MB)
3. Waits for processing
4. Asks first question

**Expected Behavior:**
```
- Upload succeeds (file within 10MB limit after compression)
- Processing takes ~30 seconds
- "Your PDF is ready!" notification
- Simple Q&A interface appears
```

**Test Question:**
> "What is the Preamble of Indian Constitution?"

**Expected AI Response:**
```
The Preamble of the Indian Constitution is an introductory statement 
that outlines the guiding principles and philosophy of the Constitution.

Key elements include:
• Sovereign, Socialist, Secular, Democratic Republic
• Justice (social, economic, political)
• Liberty (thought, expression, belief)
• Equality (status and opportunity)
• Fraternity (dignity and unity)

📖 Source: Your uploaded PDF, Page 23

Was this helpful? [👍] [👎]
```

**Roadmap Changes:**
```json
{
  "tasks_added": [
    {"title": "Read Preamble section", "type": "study", "priority": 8},
    {"title": "Take quiz on Preamble", "type": "quiz", "priority": 6}
  ],
  "estimated_completion": "2 days"
}
```

### Test Scenario 1.2: First Quiz Attempt

**User Actions:**
1. Clicks "Generate Quiz"
2. Takes 10-question quiz
3. Scores 4/10 (40%)
4. Reviews answers

**Expected Behavior:**
```
- Quiz generates in <10 seconds
- Questions match PDF content
- Score displayed with encouragement
- Explanations shown for wrong answers
```

**Expected UI Message:**
```
Score: 40% | Not quite there yet!

Don't worry - this is your first attempt. 
Focus on the topics you missed and try again.

🔄 Retake Quiz | 📖 Review Material
```

**Roadmap Changes:**
```json
{
  "weak_topics_identified": ["preamble", "fundamental_rights"],
  "tasks_updated": [
    {"title": "Revise Preamble", "type": "revision", "priority": 9},
    {"title": "Retake Polity Quiz", "type": "quiz", "scheduled": "+2 days"}
  ]
}
```

---

## 👤 Persona 2: Inconsistent User (Rahul)

### Profile
- **Age:** 26
- **Background:** Working professional, 2nd attempt
- **Tech comfort:** High
- **Study materials:** Multiple sources, disorganized
- **Time available:** 2-3 hours/day (irregular)
- **Motivation:** Variable, easily distracted

### Test Scenario 2.1: Returns After 5-Day Gap

**User Actions:**
1. Logs in after 5 days
2. Sees missed tasks
3. Asks where to continue

**Expected Behavior:**
```
- Dashboard shows streak broken
- Gentle reminder, not guilt-tripping
- "Pick up where you left off" option
- Reduced task load for comeback
```

**Expected Dashboard Message:**
```
Welcome back, Rahul! 👋

You were away for 5 days. No worries - let's ease back in.

Today's Focus (Lighter load):
☐ Quick revision: Last studied topic
☐ 5-minute quiz check

Your progress is saved. Ready to continue?
[Resume Study →]
```

**Test Question:**
> "I forgot what I studied last time, can you remind me?"

**Expected AI Response:**
```
Based on your last session (5 days ago), you were studying:

📚 Topic: Fundamental Rights (Article 14-18)
📊 Progress: 60% complete
📝 Quiz Score: 70% on this topic

Key points you covered:
1. Right to Equality (Article 14)
2. Prohibition of discrimination (Article 15)
3. Equality of opportunity (Article 16)

Shall I give you a quick 5-question recap quiz?
[Yes, quiz me] [No, continue reading]
```

**Roadmap Changes:**
```json
{
  "consistency_score": "decreased by 15%",
  "recommendations": [
    "Set smaller daily goals",
    "Enable reminder notifications"
  ],
  "tasks_adjusted": [
    {"title": "Quick revision quiz", "duration": "5 mins", "priority": 10},
    {"title": "Resume Fundamental Rights", "duration": "30 mins"}
  ]
}
```

### Test Scenario 2.2: Studies at Odd Hours (11 PM)

**User Actions:**
1. Logs in at 11:30 PM
2. Uploads new PDF
3. Asks complex question

**Expected Behavior:**
```
- No judgment about late hours
- Gentle suggestion to keep session short
- Full functionality available
- Track late-night study pattern
```

**Expected AI Response Prefix:**
```
(If pattern repeats 3+ times)

💡 Tip: I notice you often study late at night. 
While dedication is great, quality rest improves retention!

Now, to answer your question...
```

---

## 👤 Persona 3: High-Performing User (Meera)

### Profile
- **Age:** 24
- **Background:** UPSC rank holder friend, knows the game
- **Tech comfort:** High
- **Study materials:** Well-organized, multiple sources
- **Time available:** 10+ hours/day
- **Motivation:** Extremely high, systematic

### Test Scenario 3.1: Power User Behavior

**User Actions:**
1. Uploads 5 PDFs in one session
2. Generates quizzes for each
3. Asks 20+ questions
4. Achieves 90%+ on all quizzes

**Expected Behavior:**
```
- Rate limiting kicks in smoothly
- "You're on fire! 🔥" encouragement
- Advanced features suggested
- No blocking, just gentle throttling
```

**Expected Rate Limit Message:**
```
You're on a roll, Meera! 🌟

To ensure quality responses, we're processing your requests 
one at a time. Your next question will be answered in ~30 seconds.

While waiting: Review your notes on the last topic?
```

**Roadmap Changes:**
```json
{
  "performance_tier": "high_performer",
  "recommendations": [
    "Move to advanced topics",
    "Try previous year questions",
    "Practice answer writing"
  ],
  "bonus_content_unlocked": [
    "Advanced Polity: Federal debates",
    "PYQ Analysis: Constitution"
  ],
  "daily_target": "increased to 8 hours"
}
```

### Test Scenario 3.2: Challenging the AI

**User Actions:**
1. Asks nuanced UPSC question
2. Points out error in AI response
3. Asks follow-up with PYQ reference

**Test Question:**
> "In the 2019 prelims, there was a question about the difference between Fundamental Rights and DPSP. What's the UPSC's expected answer format?"

**Expected AI Response:**
```
Great question! For UPSC Prelims, the expected understanding is:

Fundamental Rights vs DPSP:

| Aspect | Fundamental Rights | DPSP |
|--------|-------------------|------|
| Enforceable | Yes, in court | No, not justiciable |
| Nature | Negative obligations | Positive obligations |
| Origin | US Constitution | Irish Constitution |
| Part | Part III | Part IV |

UPSC often tests:
- Article 37 (non-justiciability of DPSP)
- Minerva Mills case (harmony between FR & DPSP)
- Article 31C implications

⚠️ Note: Always verify with official UPSC sources.

📖 Source: Your Constitutional Law PDF, Pages 45-52

[Ask follow-up] [See related PYQs]
```

**If User Corrects AI:**
```
User: "Actually, Article 31C was modified by 42nd Amendment"

AI Response:
You're absolutely right! Thank you for the correction. 🙏

The 42nd Amendment (1976) expanded Article 31C, but the 
Supreme Court in Minerva Mills (1980) struck down part of 
this expansion.

I've noted this feedback to improve future responses.

Would you like to explore the Minerva Mills judgment in detail?
```

---

## 📋 Test Case Summary

### Beginner (Priya) Test Cases
| ID | Scenario | Expected Outcome | Priority |
|----|----------|-----------------|----------|
| B1 | First upload | Success with encouragement | High |
| B2 | Simple question | Clear, sourced answer | High |
| B3 | Failed quiz | Supportive message + revision | High |
| B4 | Overwhelmed | Simplified roadmap | Medium |

### Inconsistent (Rahul) Test Cases
| ID | Scenario | Expected Outcome | Priority |
|----|----------|-----------------|----------|
| I1 | Return after gap | Gentle re-engagement | High |
| I2 | Partial task completion | Acknowledge progress | Medium |
| I3 | Late night study | No judgment, gentle tip | Low |
| I4 | Motivation dip | Encouragement + smaller goals | Medium |

### High-Performer (Meera) Test Cases
| ID | Scenario | Expected Outcome | Priority |
|----|----------|-----------------|----------|
| H1 | Rapid usage | Smooth rate limiting | High |
| H2 | Complex questions | Nuanced, detailed answers | High |
| H3 | Corrects AI | Graceful acknowledgment | Medium |
| H4 | Demands more | Advanced content unlock | Medium |

---

## 🧪 Automated Test Commands

```python
# Run these scenarios
pytest tests/scenarios/test_beginner_flow.py
pytest tests/scenarios/test_inconsistent_flow.py
pytest tests/scenarios/test_power_user_flow.py

# Load test for rate limiting
locust -f tests/load/test_rate_limits.py --users 100
```
