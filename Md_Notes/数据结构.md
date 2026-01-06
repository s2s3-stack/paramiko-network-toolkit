# 列表
extend
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']
friends.extend(friend_number) #将列表放在最后面
print(friends)
```
append
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']
friends.append('client') #将新家数据放在列表最后面
print(friends)
```

insert
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']
friends.insert('1:gant') #在索引1前面加上gant数据
print(friends)
```
remote
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']
friends.remote('ali') #移除ali字段，括号中也可以跟索引
print(friends)
```
clear
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']
friends.clear() #移除friends列表中的数据
print(friends)
```
pop
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']
friends.pop() #移除列表中的最后一个元素
print(friends)
```
index
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','niopen','yiyi']

print(friends.index("ali")) #检查ali是否在friends列表中，如果在，将返回对应索引
```
count
```python
friend_number = [1,2,3,4,5]
friends = ['japan','ali','ali','niopen','yiyi']

print(friends.count("ali")) #计算ali在friends列表出现的次数
```
sort
```python
friends = ['japan','ali','ali','niopen','yiyi']
friends.sort() #将friends列表的按首字母正向排序
print(friends)
```
reverse
```python
friends = ['japan','ali','ali','niopen','yiyi']
friends.reverse() #将列表按照反向展示
print(friends)
```
copy
```python
friends = ['japan','ali','ali','niopen','yiyi']
friend = friends.copy() #将列表复制，赋给新的变量
print(friend)
```
# 元组 #数组不可变，不可修改删除元组元素

```python
friends = ('japan','ali','ali','niopen','yiyi')
friend = friends.insert(0,'yiyi') #执行会报错，因为元组不
print(friend)
```
