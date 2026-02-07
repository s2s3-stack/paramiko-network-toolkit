int i, j, v, k = 0;
int temp = 0;

M->rows = r;
M->cols = c;
M->terms = 0;           // 刚开始没有元素

// 第一次读入
scanf("%d %d %d", &i, &j, &v);

// 当 i 或 j 为负数时结束输入（常见约定）
while (i >= 0 && i < r && j >= 0 && j < c) {

    temp = 0;
    
    // 第一层 while：跳过 行号 < 当前 i 的所有元素
    while (temp >= 0 && temp < M->terms && M->tri[temp].i < i)
        temp++;

    // 第二层 while：同一行内，跳过 列号 < 当前 j 的元素
    while (temp >= 0 && temp < M->terms && M->tri[temp].i == i && M->tri[temp].j < j)
        temp++;

    // 此时 temp 就是应该插入的位置（或者正好是已有相同 (i,j) 的位置）

    // 后移所有元素，给 temp 位置腾出空间
    for (k = M->terms; k > temp; k--) {
        M->tri[k].i = M->tri[k-1].i;
        M->tri[k].j = M->tri[k-1].j;
        M->tri[k].v = M->tri[k-1].v;
    }

    // 插入新元素
    M->tri[temp].i = i;   // 注意这里用的是 temp，而不是 k
    M->tri[temp].j = j;
    M->tri[temp].v = v;

    M->terms++;           // 非0元素个数增加

    // 继续读下一组
    scanf("%d %d %d", &i, &j, &v);
}

return TRUE;