# Face Recognition Parameter Settings

## ✅ Current Balanced Settings (Recommended)

These parameters are optimized for real-world photos with a balance between accuracy and leniency.

### Core Parameters

| Parameter | Value | Purpose | Why This Value? |
|-----------|-------|---------|-----------------|
| `min_face_size` | **60px** | Minimum face size to process | Catches visible faces without being too strict. Small enough to include faces in group photos, large enough to filter tiny/unclear faces |
| `quality_threshold` | **0.35** | Minimum detection quality | Balanced - accepts most visible faces while filtering obviously poor detections |
| `distance_threshold` | **0.52** | Match strictness (cosine distance) | More lenient to prevent splitting same person into multiple folders |
| `min_quality_for_db` | **0.45** | Quality needed to add embedding to database | Allows good quality faces to build person profiles |
| `max_embeddings_per_person` | **30** | Max embeddings stored per person | Enough variety for robust matching without database bloat |

### Adaptive Threshold Modifiers

| Quality Range | Threshold Adjustment | Effective Range |
|---------------|---------------------|-----------------|
| Very High (>0.8) | 0.92× (stricter) | 0.48 |
| Normal (0.4-0.8) | 1.0× (standard) | 0.52 |
| Low (<0.4) | 1.15× (lenient) | 0.60 |

### Quality Weighting

- **Quality vs Size ratio:** 60% quality, 40% size
- **Minimum weight factor:** 0.5 (prevents over-penalization)

## 📊 Comparison with Previous Settings

| Parameter | Too Strict (Previous) | Balanced (Current) | Too Lenient |
|-----------|----------------------|-------------------|-------------|
| min_face_size | 100px ❌ | **60px** ✅ | 30px ⚠️ |
| quality_threshold | 0.5 ❌ | **0.35** ✅ | 0.2 ⚠️ |
| distance_threshold | 0.42 ❌ | **0.52** ✅ | 0.65 ⚠️ |
| min_quality_for_db | 0.6 ❌ | **0.45** ✅ | 0.25 ⚠️ |

## 🎯 Expected Behavior

### ✅ What Should Work Well

1. **Visible Faces:** All clearly visible faces should be detected and processed
2. **Same Person:** Photos of the same person should go into one folder
3. **Group Photos:** Each person in a group photo should be correctly identified
4. **Varying Quality:** Works with mix of high/low quality photos
5. **Different Angles:** Handles front view, side profiles, different lighting

### ⚠️ Known Limitations

1. **Very Small Faces:** Faces smaller than 60px will be skipped (intentional)
2. **Extreme Angles:** Very steep side profiles or partially hidden faces may be missed
3. **Poor Lighting:** Very dark or overexposed faces may not meet quality threshold
4. **Duplicates:** If same person looks very different (age, makeup, etc.), might create separate folders

## 🔧 When to Adjust

### Problem: "Same person split into multiple folders"

**Solution: Make matching MORE lenient**
```python
self.distance_threshold = 0.55  # Increase (try 0.55-0.60)
self.min_quality_for_db = 0.40  # Decrease slightly
```

### Problem: "Different people grouped together"

**Solution: Make matching MORE strict**
```python
self.distance_threshold = 0.48  # Decrease (try 0.45-0.50)
self.quality_threshold = 0.40   # Increase slightly
self.min_quality_for_db = 0.50  # Increase
```

### Problem: "Missing visible faces"

**Solution: Make detection MORE lenient**
```python
self.min_face_size = 50          # Decrease (try 40-55)
self.quality_threshold = 0.30     # Decrease (try 0.25-0.32)
```

### Problem: "Too many poor quality faces"

**Solution: Make detection MORE strict**
```python
self.min_face_size = 70          # Increase (try 70-80)
self.quality_threshold = 0.40     # Increase (try 0.40-0.45)
```

## 📝 Understanding the Numbers

### Face Size (pixels)
- **30-50px:** Very small, likely background faces in group photos
- **50-80px:** Small faces, usable but lower quality
- **80-150px:** Medium faces, good quality
- **150+px:** Large faces, excellent quality
- **Current threshold: 60px** - Balanced to catch small but visible faces

### Quality Score (0-1 from InsightFace)
- **0.0-0.2:** Very poor detection, likely false positive
- **0.2-0.35:** Poor quality, blurry or occluded
- **0.35-0.6:** Good quality, clear face
- **0.6-0.8:** Very good quality
- **0.8-1.0:** Excellent quality, perfect frontal face
- **Current threshold: 0.35** - Accepts most visible faces

### Cosine Distance (0-2, lower = more similar)
- **0.0-0.3:** Very similar, definitely same person
- **0.3-0.5:** Similar, likely same person
- **0.5-0.7:** Somewhat similar, might be same person
- **0.7-1.0:** Different people
- **1.0+:** Very different
- **Current threshold: 0.52** - Matches within "similar" range

## 🧪 Testing Workflow

1. **Start Small:** Test with 10-20 photos first
2. **Check Console:** Look at quality scores and distances in output
3. **Verify Results:** 
   - Are visible faces being detected? ✅
   - Same person in one folder? ✅
   - Different people separated? ✅
4. **Adjust if Needed:** Use guidelines above
5. **Full Run:** Process entire collection once satisfied

## 💡 Pro Tips

1. **Watch the Console Output:**
   - `⚠️ Face too small` → Many of these? Reduce min_face_size
   - `⚠️ Face low quality` → Many of these? Reduce quality_threshold
   - `❓ No match found` → Too many? Increase distance_threshold
   - `🎯 Best match` with high distances (>0.5) → Threshold might be too high

2. **Quality Score Patterns:**
   - Most faces scoring 0.6-0.9? → Can increase quality_threshold
   - Most faces scoring 0.3-0.5? → Keep current settings
   - Many faces below 0.3? → Photo quality issue or threshold too low

3. **Distance Patterns:**
   - Matches consistently <0.4? → Can decrease threshold for stricter matching
   - Matches often 0.5-0.6? → Current threshold is good
   - Matches approaching threshold? → Might need to increase threshold

## 🔄 Quick Presets

### Conservative (Fewer false matches, might split people)
```python
min_face_size=70
quality_threshold=0.40
distance_threshold=0.48
min_quality_for_db=0.50
```

### Balanced (Current - Recommended)
```python
min_face_size=60
quality_threshold=0.35
distance_threshold=0.52
min_quality_for_db=0.45
```

### Aggressive (Groups more together, might merge different people)
```python
min_face_size=50
quality_threshold=0.30
distance_threshold=0.58
min_quality_for_db=0.40
```

---

**Last Updated:** After user feedback on strict parameters  
**Status:** Balanced settings for real-world usage ✅

