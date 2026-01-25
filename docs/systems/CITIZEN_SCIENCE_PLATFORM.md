# Mycosoft Citizen Science Platform

## Overview

The Mycosoft Citizen Science Platform enables public participation in fungal data collection, creating a global network of observers contributing to MINDEX and advancing mycological research.

## Platform Components

### Mobile Application

**MycoScout** - Available on iOS and Android

#### Core Features
1. **Photo Identification**
   - AI-powered species recognition
   - Multi-angle photo capture
   - Spore print documentation
   - Habitat recording

2. **Observation Logging**
   - GPS location (with privacy options)
   - Date/time stamps
   - Weather conditions (automatic)
   - Substrate type selection
   - Associated species

3. **Gamification**
   - Observer levels (Novice → Expert)
   - Achievement badges
   - Species collection tracking
   - Regional leaderboards
   - Seasonal challenges

4. **Community**
   - Expert verification
   - Discussion forums
   - Local group organization
   - Event calendar
   - Mentorship matching

### Web Platform

**mycoscout.mycosoft.com**

- Full observation management
- Data export tools
- Research collaboration
- Educational resources
- API access for researchers

### Data Quality System

#### Verification Levels
1. **Casual** - Basic photo, limited metadata
2. **Needs ID** - Good photos, awaiting identification
3. **Research Grade** - Expert verified, complete metadata
4. **Voucher Collected** - Physical specimen preserved

#### Quality Scoring
```
Quality Score = 
  (Photo Quality × 0.3) +
  (Metadata Completeness × 0.2) +
  (Community Agreement × 0.3) +
  (Expert Verification × 0.2)
```

## Integration with MINDEX

### Data Flow
```
Observer App → Validation → MINDEX Staging → Review → MINDEX Production
      ↓              ↓            ↓              ↓
   Photos     AI Confidence   Community IDs   Expert QC
```

### Contribution Attribution
- All contributors credited in MINDEX
- DOI for major datasets
- Research paper acknowledgment policy
- Contributor statistics public

## Gamification System

### Levels

| Level | Title | XP Required | Perks |
|-------|-------|-------------|-------|
| 1 | Spore | 0 | Basic features |
| 2 | Mycelium | 100 | Photo hints |
| 3 | Primordium | 500 | ID suggestions |
| 4 | Button | 2,000 | Verification voting |
| 5 | Cap | 5,000 | Species claiming |
| 6 | Sporulating | 15,000 | Expert status |
| 7 | Network | 50,000 | Research access |
| 8 | Elder | 100,000 | All features |

### XP Earning

| Action | XP |
|--------|-----|
| Submit observation | 10 |
| Research grade achieved | 50 |
| Correct identification | 25 |
| First to find (region) | 100 |
| Species new to platform | 500 |
| Help identify others | 15 |
| Referred new user | 75 |

### Badges

#### Discovery Badges
- 🍄 First Find - First observation
- 🔍 Eagle Eye - 10 accurate IDs
- 🌍 World Traveler - Observations from 5+ countries
- 📸 Photographer - 100 research-grade photos
- 🧬 Rare Hunter - Found endangered species

#### Seasonal Badges
- 🌸 Spring Flush - 20 spring observations
- ☀️ Summer Surveyor - 30 summer observations
- 🍂 Fall Forager - 50 autumn observations
- ❄️ Winter Warrior - 10 winter observations

#### Community Badges
- 🎓 Mentor - Helped 10 new users
- ✅ Verifier - 100 correct verifications
- 👥 Group Leader - Organized local event
- 📚 Educator - Created learning content

## Mobile App Architecture

### Technology Stack
- **Framework**: React Native
- **State**: Redux Toolkit
- **Maps**: Mapbox
- **Camera**: Expo Camera
- **AI**: TensorFlow Lite (on-device)
- **Backend**: MINDEX API

### Offline Capabilities
- Observation drafts
- Local species database
- Queue for upload
- Cached identification
- GPS without network

### Privacy Features
- Location fuzzing (1km radius option)
- Private observations
- Anonymous mode
- Data export/deletion

## Research Collaboration

### Partner Benefits
- API access to observations
- Custom data exports
- Priority verification
- Acknowledgment template
- Publication support

### Data Licensing
- CC BY-NC 4.0 default
- Researcher-specific agreements
- Commercial use negotiation
- Indigenous data sovereignty

### Active Research Projects
1. Climate change phenology study
2. Urban biodiversity mapping
3. Rare species distribution
4. Pollution biomonitoring
5. Edibility documentation

## Monetization

### Free Tier
- Unlimited observations
- Basic AI identification
- Community features
- Standard badges

### Premium ($4.99/month)
- Advanced AI (higher accuracy)
- Detailed species profiles
- Offline full database
- Ad-free experience
- Priority support

### Research Tier ($29.99/month)
- Full data export
- API access
- Bulk upload
- Advanced analytics
- Custom fields

## Launch Plan

### Phase 1: Beta (Q1 2026)
- iOS app development
- Core observation features
- Basic AI identification
- 1,000 beta testers

### Phase 2: Public Launch (Q2 2026)
- Android release
- Web platform
- Gamification system
- iNaturalist data import

### Phase 3: Growth (Q3 2026)
- Research partnerships
- Premium features
- API marketplace
- Educational content

### Phase 4: Scale (Q4 2026)
- International expansion
- Language localization
- Regional ambassadors
- University partnerships

## Metrics & Goals

### Year 1 Targets
- 50,000 registered users
- 500,000 observations
- 75% species coverage (common)
- 10 research partnerships
- $100,000 revenue

### Key Performance Indicators
- Daily Active Users (DAU)
- Observations per user
- Research grade rate
- Retention (D7, D30)
- AI accuracy improvement

## Team Requirements

- Mobile Developer (iOS/Android)
- Backend Developer (MINDEX integration)
- ML Engineer (identification model)
- Community Manager
- Mycology Advisor
- UI/UX Designer

---

*Document Version: 1.0*
*Last Updated: 2026-01-24*
*Classification: Product Specification*
