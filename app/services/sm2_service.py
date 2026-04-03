from datetime import datetime, timedelta


class SM2Service:
    """SM-2 spaced repetition algorithm.

    Rating scale (0-5):
        0 - Complete blackout
        1 - Incorrect, but upon seeing the answer, remembered
        2 - Incorrect, but the answer seemed easy to recall
        3 - Correct with serious difficulty
        4 - Correct after hesitation
        5 - Perfect response
    """

    MIN_EASE_FACTOR = 1.3

    @classmethod
    def review(cls, flashcard, rating):
        """Apply SM-2 algorithm and return updated parameters.

        Args:
            flashcard: Flashcard model instance.
            rating: Integer 0-5.

        Returns:
            Dict with updated ease_factor, interval, repetitions, next_review_at.
        """
        rating = max(0, min(5, rating))

        ease_factor = flashcard.ease_factor
        interval = flashcard.interval
        repetitions = flashcard.repetitions

        if rating >= 3:
            # Correct response
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = round(interval * ease_factor)

            repetitions += 1
            ease_factor = ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
        else:
            # Incorrect response — reset
            repetitions = 0
            interval = 1

        # Enforce minimum ease factor
        ease_factor = max(cls.MIN_EASE_FACTOR, ease_factor)

        next_review_at = datetime.utcnow() + timedelta(days=interval)

        return {
            'ease_factor': round(ease_factor, 4),
            'interval': interval,
            'repetitions': repetitions,
            'next_review_at': next_review_at,
        }
