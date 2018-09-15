from comments.models import CommentsHistory
from core import celery_app


@celery_app.task
def export_comments_history(obj_id):
    obj = CommentsHistory.objects.get(pk=obj_id)
    obj.export()
