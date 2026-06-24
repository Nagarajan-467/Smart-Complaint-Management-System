"""
Clustering Engine.
Uses unsupervised Machine Learning (K-Means) to group similar unresolved complaints,
allowing administrators to spot massive, widespread issues.
"""

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatus


def run_clustering(db: Session) -> list[Complaint]:
    """
    Fetches all unresolved complaints, vectorizes their text, and clusters them using KMeans.
    The resulting cluster_id is saved directly to the database.
    """
    stmt = select(Complaint).where(
        Complaint.status.in_([
            ComplaintStatus.PENDING, 
            ComplaintStatus.ASSIGNED, 
            ComplaintStatus.IN_PROGRESS
        ])
    )
    complaints = list(db.scalars(stmt).all())
    
    # We need a minimum number of complaints to make clustering meaningful
    if len(complaints) < 3:
        return []
        
    # Build text corpus combining Title, Description, and Location
    texts = [f"{c.title} {c.description} {c.location or ''}" for c in complaints]
    
    # Vectorize
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        X = vectorizer.fit_transform(texts)
    except ValueError:
        return []
        
    # Dynamic Cluster Sizing Strategy:
    # Aim for roughly 3-5 complaints per cluster
    k = max(2, len(complaints) // 3)
    k = min(k, len(complaints))  # Cannot have more clusters than samples
    
    # Run K-Means Clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
    kmeans.fit(X)
    
    clusters = kmeans.labels_
    
    # Save the computed cluster IDs back to the database
    for idx, complaint in enumerate(complaints):
        complaint.cluster_id = int(clusters[idx])
        
    db.commit()
    
    return complaints
