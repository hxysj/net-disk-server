from django.db import models
from FileInfo.models import FileInfo
from User.models import User


# Create your models here.


class FileShare(models.Model):
    share_id = models.CharField('分享id', max_length=40, primary_key=True)
    file_id = models.ForeignKey(FileInfo, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    valid_type = models.IntegerField('有效期类型')
    expire_time = models.DateTimeField('失效时间')
    share_time = models.DateTimeField('分享时间', auto_now_add=True)
    show_count = models.IntegerField('浏览次数', default=0)
    code = models.CharField('分享的提取码:', max_length=5)

    class Meta:
        db_table = 'file_share'

    def viewed(self):
        self.show_count += 1
        self.save(update_fields=['show_count'])
