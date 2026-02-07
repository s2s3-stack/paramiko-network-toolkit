JDBC技术基础
	JDBC是一种可以执行SQL语句的Java API。后台的数据库安装好之后，前台的Java 程序是不能直接访问数据库的，必须要通过相应的数据库驱动程序
JDBC常用接口及常用方法简介
	Driver 接口
		Driver 接口由数据库厂家提供。在编程中要连接数据库，必须先加载特定厂商的数据库驱 动程序，不同数据库的加载方法不同。
			加载MySQL驱动
				Class. forName ("com.mysql.jdbc. Driver") ;
			加载Oracle驱动。
				Class. forName ("oracle.jdbc.dr iver.OracleDriver") ;
			加载SQL Server 驱动
				Class. forName ("com. microsoft.jdbc.sqlserver.SQLServerDriver")
	Connection 接口
		Connection是数据库连接对象，每个Connection代表一个物理连接会话
			Connection conn= DriverManager. getConnection (url,user, pass) ;
	Statement 接口
		Statement对象用于向数据库发送SQL语向并返回它所生成结果的对象
			Statement stmt = conn. createStatement () ;
			PreparedStatement stmt = conn. prepareStatement (sql) ;  /*返回预编译的
			Statement*/
			CallableStatement stmt = conn. prepareCall (sql) ;  / *返回执行存储过程的  Statement*/
	 ResultSet 接口
		 ResultSet对象用于执行Select语句的结果集。它采用表格的方式，可以通过列索引或列名 获得数据，并通过五种方法来移动结果集中的记录指针。ResultSet 根据查询不同类型字段， 提供不同的方法获得数据。
JDBC编程步骤
	① 加载数据库驱动
	② 通过 DriveManager 建立数据库连接，返回Connection对象。
	③ 通过 Connection对象创建 Statement 对象。
	④ 通过 Statement对象的 execute () 、executeQuery () 、executeUpdate () 方法执
	行SQL语句。
	⑤ 如果第④步执行的是查询语句，则对结果集 (ResultSet) 进行操作。
	⑥ 结束时，回收数据库资源，包括关闭ResultSet、Statement 和Connection等资源。

			




