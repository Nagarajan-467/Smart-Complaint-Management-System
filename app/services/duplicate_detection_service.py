"""
Duplicate Complaint Detection Engine.
Uses TF-IDF and Cosine Similarity to find semantic duplicates.
"""

from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintCategory, ComplaintStatus


def detect_duplicate(
    db: Session, 
    title: str, 
    description: str, 
    category: ComplaintCategory,
    threshold: float = 0.75
) -> Optional[int]:
    """
    Compares the new complaint against unresolved complaints in the same category.
    Returns the ID of the duplicate complaint if similarity > threshold, else None.
    """
    # 1. Fetch existing unresolved complaints in the same category
    stmt = select(Complaint).where(
        Complaint.status.in_([
            ComplaintStatus.PENDING, 
            ComplaintStatus.ASSIGNED, 
            ComplaintStatus.IN_PROGRESS
        ]),
        Complaint.category == category
    )
    existing_complaints = list(db.scalars(stmt).all())
    
    if not existing_complaints:
        return None
        
    # 2. Prepare text corpus
    # We combine title and description for richer semantic context
    existing_texts = [f"{c.title} {c.description}" for c in existing_complaints]
    new_text = f"{title} {description}"
    
    # Add the new complaint text to the end of the list to vectorize everything together
    all_texts = existing_texts + [new_text]
    
    # 3. Vectorize text using TF-IDF (Term Frequency-Inverse Document Frequency)
    # Stop words are removed to prevent common words ("the", "is") from inflating similarity
    vectorizer = TfidfVectorizer(stop_words='english')
    
    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        # This can happen if texts only contain stop words (e.g., "is it")
        return None
        
    # 4. Calculate cosine similarity
    # Compare the new text (last row) against all existing texts (all previous rows)
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    
    # 5. Find the best match
    max_sim_idx = cosine_sim.argmax()
    max_sim_score = cosine_sim[max_sim_idx]
    
    # 6. Flag as duplicate if score exceeds threshold
    if max_sim_score > threshold:
        return existing_complaints[max_sim_idx].id
        
    return None
