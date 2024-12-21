from django.db import models
from User.models import User


class FileInfo(models.Model):
    file_id = models.CharField('文件id', max_length=40, primary_key=True, unique=True)
    file_md5 = models.CharField('文件md5值', max_length=32, default='')
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    file_pid = models.CharField('父级id', max_length=40, default='0')
    file_size = models.IntegerField('文件大小', null=True)
    file_name = models.CharField('文件名称', max_length=200)
    file_cover = models.ImageField('文件封面', upload_to='cover', default='')
    file_path = models.FileField('文件位置', upload_to='file', default='')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    last_update_time = models.DateTimeField('修改时间', auto_now=True)
    folder_type = models.IntegerField('文件类型')
    file_category = models.IntegerField('文件分类', null=True)
    file_type = models.IntegerField('文件具体分类', null=True)
    status = models.IntegerField('文件状态', default=2)
    recovery_time = models.DateTimeField('进入回收站时间', null=True)
    del_flag = models.IntegerField('文件是否删除', default=2)

    class Meta:
        db_table = 'file_info'