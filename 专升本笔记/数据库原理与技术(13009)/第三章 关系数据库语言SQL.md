SQL数据库的特点
	SQL数据库的特点
	一个表由若干行和若干列组成
	表有三种类型：
		基本表：是用来存储数据的
		视图：是由若干基本表或其他视图构成的表的定义，是虚拟表，并不真正存储 数据
		导出表：是执行查询时产生的临时表，存储在内存或数据缓冲区
	SQL的组成
		数据定义功能
			通过数据定义语言 (DDL) 来定义SQL数据库 (Database) 、基本表 (
			Table) 、视图 (View) 、索引 (Index) 等结构
		数据操纵功能
			通过数据操纵语言 (DML) 来实现对数据库的操纵，包括查询和更新两种操作
		数据控制功能
			通过数据控制语言 (DCL) 来实现数据库恢复、完整性、并发、安全性控制
		嵌入式SQL使用规则
			SQL嵌入到宿主语言 (如C语言) 程序中使用的规则
数据库的定义功能
	数据库的创建
		Create database <数据库名>
	数据库的删除
		Drop  database <数据库名>
	基本表的创建
		Create Table <表名>
	基本表的修改
		Alter Table <表名>
	基本表的删除
		Drop Table <表名>
	索引的创建
		Create Index <索引名>
			ASC //升序,默认
			DESC //降序 
	索引的删除
		Drop Index <索引名>
SQL的数据更新
	插入数据
		Insert Into 表名 (字段名表) Values (内容列表)
			例如:
			Insert  Into  Student (Sno,Sname,Sage,Sdept)
			Values ( “2023005”,   “卤蛋”, 6,  “短腿系”)
	更新数据
		Update 表名 Set <列名1>=<值1>[，<列名1>=<值1>] [Where条件]
			例如：将学号为2023003的学生年龄改为25
				Update  Student  Set age=25  Where Sno=‘2023003’
	删除数据
		Delete from 表名 [Where条件]
			例如：将学生信息表中学号为  “2023002”的学生记录
				Delete   from  Student  Where Sno=‘2023002’
SQL的数据查询
	单表查询
		Select 字段名表 [Into目标表] from表名 [Where条件] [Order by字段]
		[Group by字段] [having 条件]
			Order by字段：按照指定字段排序，升序 (ASC) 、降序 (DESC) 
			Group by字段：按照指定字段分组 [having 条件]：设置分组条件
				*列名用别名显示：格式为“列名as‘别名’”,其中“as”可省略
		Case用法:
			Case when 列名=值1 Then  ‘显示1’when 列名=值2 Then  ‘显示2’...else’其他’end as  ‘别名‘。
				例如将列标题‘Sno’显示为中文“学号” ，’Sname‘显示为中文“姓名” ，查询性
				别时将性别用“男”或“女”显示
					Select Sno as‘学号’ ，Sname as  ‘姓名’Case when Sex=‘M’ then‘男‘ when Sex=’F’ then  ‘女’ else as  ‘性别’ from S
					Select distinct  Sno  from S //使用distinct可以消除重复记录
		确定范围谓词：
			between...and (介于...和...之间) ，not  between...and (不在...和...之间)
		模糊匹配:
			LIKE，NOT LIKE，% 表示包含零个或多个字符的任意字符串，_表示单个字符
				SELECT *  FROM Student  WHERE Sname LIKE  ‘刘%’
				//查询姓名字段中所有姓“刘”的同学的记录
		聚合查询
			Count (*) ：对元组个数进行计数
			Count ([All | Distinct]<列名>：对元组个数求和 (取消重复记录数)
			Sum ([All | Distinct]<列名>：按列求和 (该列必须为数值类型)
			Ave (All | Distinct<列名>：按列求平均 (该列必须为数值类型)
			 Max (All | Distinct<列名>：按列求最大值
			 Min (All | Distinct<列名>：按列求最小值
		对聚合结果进行分组:
			Group by子句可以将查询结果按一列或多列的值进行分组，值相等的分为一组，并可 以结合Having语句设置条件表达式
			例如:
			Select Cno‘课程编号’,Count (Sno)  ‘人数’,ave (Score)  ‘平均分’,       Max (Score)  ‘最高分’ ，Min (Score)  ‘最低分’ from SC group by Cno       Order by avg (Score) DESC
			//按课程号统计各门课程的选课人数、平均分、最高分、最低分，结果按平均分
			降序排，列标题用中文显示
视图的定义 使用和删除
	视图是子模式 (或用户模式) 的主要表现形式，它是以一个或多个基本表 (或已定义
	的视图) 导出的虚表，数据库中只存放视图的定义，不存放视图对应的数据
		创建视图
			Creat View<视图名>[ (列名1>[，  (列名2) ]...) ]
		删除视图
			Drop View<视图名>
	视图的作用:
		视图可以隐蔽数据的复杂性，简化用户对数据的操作
		视图可以使用户以不同的方式看待同一数据
		视图对数据库的重构提供了一定程度的逻辑独立性
		视图可以为机密的数据提供安全保护


			

	

		









		





	








		