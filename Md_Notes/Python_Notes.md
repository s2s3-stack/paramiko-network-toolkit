布尔表达(True及False的判断)比较运算符


```python
is_male = True
is_tail = False

if is_male and is_tail:
    print("这是一只公狗")
elif is_male and not is_tail: #not 取反
    print("这是一只公猫")
elif not is_male and is_tail: 
    print("这是一只母狗")

```

    这是一只公猫
    

比较运算符(> 大于,< 小于,== 等于,!= 不等于)


```python
def num(num1,num2,num3):
    if num1 > num2 and num1 > num3:
        return num1
    elif num2 > num1 and num2 > num3:
        return num2
    else:
        return num3

print(num(1,2,3))
```

    3
    

计算机的生成


```python
number1 = float(input("first number:"))
op = input("请输入一个计算操作:")
number2 = float(input("second number:"))

if op == "+":
    print(number1 + number2) 
elif op == "-":
    print(number1 - number2)
elif op == "*":
    print(number1 * number2)
```

字典


```python
monthConversions = {
    "Jan": "January",
    "Feb": "February",
    "Mar": "March",
    "Apr": "April",
    "May": "May",
}
print(monthConversions["Jan"]) #打印字典中的键
print(monthConversions.get("Dec", "Invalid Month")) #如果字典中没有这个键，则返回默认值

```

    January
    Invalid Month
    

while循环


```python
i = 1
while i <= 5:
    print(i)
    i += 1

print("Done")
```

猜词小游戏


```python
scret_word = "python"
guess = ""
guess_count = 0
guess_limit = 3
out_of_guesses = False

while guess != scret_word and not(out_of_guesses): #如果猜对了
    if guess_count < guess_limit: #如果猜的次数小于限制次数
        guess = input("Enter guess:")
        guess_count += 1
    else:
        out_of_guesses = True #如果猜的次数大于限制次数，则猜错了

if out_of_guesses: #如果猜错了
    print("Out of guesses, YOU LOSE!")
else:
    print("You win!")
```

for循环


```python
friends = ["Jim", "Karen", "Kevin"] 
for friend in range(len(friends)):
    print(friends[friend])
for index in range(3,10,2): #从3开始，到10结束，步长为2
    print(index)
for letter in "Giraffe Academy": 
    print(letter)
for number in range(5):
    if number == 0:
        print("first iteration")
    else:
        print("not first") 
```

指数运算函数


```python
def raise_to_power(base_num,pow_num):
    result = 1
    for index in range(pow_num): #循环pow_num次
        result = base_num * result

    return result

print(raise_to_power(4,4))
```

    256
    

替换函数


```python
def translate(phrse):
    translate = ''
    for letter in phrse:
        if letter.lower() in 'asdfghj':  #判断是否在指定字母内
            if letter.isupper():  #判断是否大写
                translate = translate + 'G' #大写字母对应大写
            else:
                translate = translate + 'g' #小写字母对应小写
        else:
            translate = translate + letter
    return translate


print(translate(input('输入你的字母:')))
```

try....except....


```python
try:
    answer = 10 / 0
    number = int(input("Enter a number:"))
except ZeroDivisionError as e:
    print("You can't divide by zero!")
    print(e)
except ValueError as e:
    print("Invalid input!")

```

文件操作


```python
try:
    file = open(r"C:\Users\sys400070\PycharmProjects\脚本\Py学习\text.txt", "r", encoding="utf-8")
    files = []
    for line in file.readlines():
        files.append(line.strip())
    
    file.close()  # 先关闭读模式
    
    # 重新打开写模式追加
    with open(r"C:\Users\sys400070\PycharmProjects\脚本\Py学习\text.txt", "a", encoding="utf-8") as file_2:
        file_2.write(files[2] + "\n")  # 建议加上换行符，否则会粘在一起
    
except FileNotFoundError as e:
    print("文件不存在！")
except IndexError:
    print("列表索引越界：files[2] 不存在，文件可能少于3行")
except Exception as e:
    print(f"其他错误：{e}")
```

类和对象


```python
class student:
    def __init__(self, name, major, gpa, is_on_probation):
        self.name = name
        self.major = major
        self.gpa = gpa
        self.is_on_probation = is_on_probation

student1 = student("Jim", "Business", 3.1, False)
student2 = student("Pam", "Art", 2.5, True)     
print(student1.name)
print(student2.major)

```


```python
class question: #定义一个问题类
    def __init__(self, prompt, answer): #初始化问题和答案
        self.prompt = prompt #问题
        self.answer = answer #答案

question_prompts = [   #问题列表
    "What is 2+2?\n(a)3\n(b)4\n(c)5\n\n",
    "What is the capital of France?\n(a)London\n(b)Berlin\n(c)Paris\n\n",
    "What is the color of the sky?\n(a)Blue\n(b)Green\n(c)Red\n\n"
]
questions = [ # 问题对象列表
    question(question_prompts[0], "b"),
    question(question_prompts[1], "c"),
    question(question_prompts[2], "a")
]
def run_test(questions): #定义一个测试函数
    score = 0
    for question in questions:
        answer = input(question.prompt)
        if answer == question.answer:
            score += 1
    print("You got " + str(score) + "/" + str(len(questions)))
run_test(questions)                 
```
