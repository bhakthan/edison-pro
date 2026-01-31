"""
Phase 3 Enhancements: Feedback Tracking & Learning System
Tracks usage, effectiveness, and learns from user interactions

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEvent:
    """User feedback on a suggested question or feature result"""
    event_id: str
    feature_type: str  # 'query_suggestion', 'anomaly_prediction', 'expert_review', etc.
    timestamp: datetime
    diagram_id: Optional[str]
    domain: str
    feedback_type: str  # 'helpful', 'not_helpful', 'found_issue', 'accepted', 'rejected'
    context: Dict[str, Any]
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class FeatureUsageStats:
    """Statistics for a specific feature"""
    feature_type: str
    total_uses: int
    successful_uses: int
    helpful_feedback_count: int
    issues_found_count: int
    avg_confidence: float
    avg_processing_time_ms: float
    domains: Dict[str, int]  # domain -> count
    last_used: datetime


class FeedbackTracker:
    """
    Tracks user feedback and feature usage for continuous learning
    
    Phase 3 Enhancement: Learning from user interactions
    
    Capabilities:
    1. Record feedback on all innovative features
    2. Track effectiveness scores over time
    3. Identify high-value patterns and questions
    4. Generate usage analytics
    5. Support A/B testing of different approaches
    """
    
    def __init__(self, db_path: str = "./feedback_tracking.db"):
        """
        Initialize feedback tracker with SQLite database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"📊 Feedback Tracker initialized (DB: {db_path})")
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Feedback events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_events (
                event_id TEXT PRIMARY KEY,
                feature_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                diagram_id TEXT,
                domain TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                context TEXT,
                user_id TEXT,
                INDEX idx_feature (feature_type),
                INDEX idx_timestamp (timestamp),
                INDEX idx_domain (domain)
            )
        """)
        
        # Feature usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_type TEXT NOT NULL,
                domain TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                confidence REAL,
                processing_time_ms REAL,
                result_summary TEXT,
                INDEX idx_feature_domain (feature_type, domain),
                INDEX idx_timestamp (timestamp)
            )
        """)
        
        # Question effectiveness table (for Query Suggester)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_effectiveness (
                question_id TEXT PRIMARY KEY,
                question_text TEXT NOT NULL,
                domain TEXT NOT NULL,
                category TEXT,
                times_suggested INTEGER DEFAULT 0,
                times_asked INTEGER DEFAULT 0,
                helpful_count INTEGER DEFAULT 0,
                issues_found_count INTEGER DEFAULT 0,
                effectiveness_score REAL DEFAULT 0.5,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Anomaly pattern effectiveness (for Anomaly Predictor)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_effectiveness (
                pattern_id TEXT PRIMARY KEY,
                pattern_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                times_matched INTEGER DEFAULT 0,
                true_positives INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                precision REAL,
                last_updated TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Database schema initialized")
    
    def record_feedback(self, feedback: FeedbackEvent) -> bool:
        """
        Record user feedback event
        
        Args:
            feedback: FeedbackEvent object
            
        Returns:
            Success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO feedback_events 
                (event_id, feature_type, timestamp, diagram_id, domain, feedback_type, context, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.event_id,
                feedback.feature_type,
                feedback.timestamp.isoformat(),
                feedback.diagram_id,
                feedback.domain,
                feedback.feedback_type,
                json.dumps(feedback.context),
                feedback.user_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Recorded feedback: {feedback.feature_type} - {feedback.feedback_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording feedback: {e}")
            return False
    
    def record_feature_usage(
        self,
        feature_type: str,
        domain: str,
        success: bool,
        confidence: Optional[float] = None,
        processing_time_ms: Optional[float] = None,
        result_summary: Optional[str] = None
    ) -> bool:
        """Record feature usage for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO feature_usage 
                (feature_type, domain, timestamp, success, confidence, processing_time_ms, result_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                feature_type,
                domain,
                datetime.utcnow().isoformat(),
                success,
                confidence,
                processing_time_ms,
                result_summary
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error recording usage: {e}")
            return False
    
    def update_question_effectiveness(
        self,
        question_id: str,
        question_text: str,
        domain: str,
        category: str,
        was_asked: bool = False,
        was_helpful: bool = False,
        found_issue: bool = False
    ):
        """Update effectiveness score for a suggested question"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if question exists
            cursor.execute("""
                SELECT times_suggested, times_asked, helpful_count, issues_found_count, effectiveness_score
                FROM question_effectiveness
                WHERE question_id = ?
            """, (question_id,))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing
                times_suggested, times_asked, helpful_count, issues_found, current_score = row
                
                times_suggested += 1
                if was_asked:
                    times_asked += 1
                if was_helpful:
                    helpful_count += 1
                if found_issue:
                    issues_found += 1
                
                # Calculate new effectiveness score
                # Formula: weighted average of helpfulness and issue discovery
                ask_rate = times_asked / max(times_suggested, 1)
                helpful_rate = helpful_count / max(times_asked, 1) if times_asked > 0 else 0
                issue_rate = issues_found / max(times_asked, 1) if times_asked > 0 else 0
                
                # New score: 0.3 * ask_rate + 0.4 * helpful_rate + 0.3 * issue_rate
                new_score = 0.3 * ask_rate + 0.4 * helpful_rate + 0.3 * issue_rate
                
                # Apply exponential moving average with old score
                effectiveness_score = 0.7 * new_score + 0.3 * current_score
                
                cursor.execute("""
                    UPDATE question_effectiveness
                    SET times_suggested = ?, times_asked = ?, helpful_count = ?, 
                        issues_found_count = ?, effectiveness_score = ?, last_updated = ?
                    WHERE question_id = ?
                """, (times_suggested, times_asked, helpful_count, issues_found, 
                      effectiveness_score, datetime.utcnow().isoformat(), question_id))
            else:
                # Insert new
                effectiveness_score = 0.5  # Default
                if was_asked:
                    effectiveness_score = 0.6
                if was_helpful:
                    effectiveness_score = 0.7
                if found_issue:
                    effectiveness_score = 0.9
                
                cursor.execute("""
                    INSERT INTO question_effectiveness
                    (question_id, question_text, domain, category, times_suggested, times_asked,
                     helpful_count, issues_found_count, effectiveness_score, last_updated)
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """, (question_id, question_text, domain, category,
                      1 if was_asked else 0,
                      1 if was_helpful else 0,
                      1 if found_issue else 0,
                      effectiveness_score,
                      datetime.utcnow().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated question effectiveness: {question_id} -> {effectiveness_score:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating question effectiveness: {e}")
            return False
    
    def get_top_questions(
        self,
        domain: str,
        limit: int = 10,
        min_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Get most effective questions for a domain"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT question_id, question_text, category, times_suggested, times_asked,
                       helpful_count, issues_found_count, effectiveness_score
                FROM question_effectiveness
                WHERE domain = ? AND effectiveness_score >= ?
                ORDER BY effectiveness_score DESC, issues_found_count DESC
                LIMIT ?
            """, (domain, min_score, limit))
            
            questions = []
            for row in cursor.fetchall():
                questions.append({
                    'question_id': row[0],
                    'question_text': row[1],
                    'category': row[2],
                    'times_suggested': row[3],
                    'times_asked': row[4],
                    'helpful_count': row[5],
                    'issues_found': row[6],
                    'effectiveness_score': row[7]
                })
            
            conn.close()
            return questions
            
        except Exception as e:
            logger.error(f"❌ Error getting top questions: {e}")
            return []
    
    def get_feature_stats(self, feature_type: str) -> Optional[FeatureUsageStats]:
        """Get usage statistics for a feature"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_uses,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_uses,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time_ms) as avg_time,
                    MAX(timestamp) as last_used
                FROM feature_usage
                WHERE feature_type = ?
            """, (feature_type,))
            
            row = cursor.fetchone()
            if not row or row[0] == 0:
                conn.close()
                return None
            
            total_uses, successful_uses, avg_conf, avg_time, last_used = row
            
            # Domain breakdown
            cursor.execute("""
                SELECT domain, COUNT(*) as count
                FROM feature_usage
                WHERE feature_type = ?
                GROUP BY domain
            """, (feature_type,))
            
            domains = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Feedback counts
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN feedback_type = 'helpful' THEN 1 ELSE 0 END) as helpful_count,
                    SUM(CASE WHEN feedback_type = 'found_issue' THEN 1 ELSE 0 END) as issues_count
                FROM feedback_events
                WHERE feature_type = ?
            """, (feature_type,))
            
            feedback_row = cursor.fetchone()
            helpful_count = feedback_row[0] or 0
            issues_count = feedback_row[1] or 0
            
            conn.close()
            
            return FeatureUsageStats(
                feature_type=feature_type,
                total_uses=total_uses,
                successful_uses=successful_uses or 0,
                helpful_feedback_count=helpful_count,
                issues_found_count=issues_count,
                avg_confidence=avg_conf or 0.0,
                avg_processing_time_ms=avg_time or 0.0,
                domains=domains,
                last_used=datetime.fromisoformat(last_used)
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting feature stats: {e}")
            return None
    
    def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        features = [
            'anomaly_prediction',
            'revision_analysis',
            'query_suggestion',
            'expert_review',
            'counterfactual_simulation'
        ]
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'features': {}
        }
        
        for feature in features:
            stats = self.get_feature_stats(feature)
            if stats:
                report['features'][feature] = {
                    'total_uses': stats.total_uses,
                    'success_rate': stats.successful_uses / stats.total_uses if stats.total_uses > 0 else 0,
                    'avg_confidence': stats.avg_confidence,
                    'avg_processing_time_ms': stats.avg_processing_time_ms,
                    'helpful_feedback_count': stats.helpful_feedback_count,
                    'issues_found': stats.issues_found_count,
                    'domains': stats.domains,
                    'last_used': stats.last_used.isoformat()
                }
        
        return report


def create_feedback_tracker(db_path: str = "./feedback_tracking.db") -> FeedbackTracker:
    """Factory function to create feedback tracker"""
    return FeedbackTracker(db_path=db_path)
