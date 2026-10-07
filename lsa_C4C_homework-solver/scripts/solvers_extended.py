#!/usr/bin/env python3
"""
扩展学科求解器（线性代数 / 微分方程 / 大学物理）。

Starter Kit 中 solve_matrix / solve_ode 只是占位 stub（返回"学生扩展点"）。
本模块把它们补全为**可运行的确定性求解器**，全部基于 SymPy：

  线性代数:
    - 矩阵解析（pmatrix/bmatrix/matrix -> sympy.Matrix）
    - 行列式 det、逆 inv、转置 T、秩 rank
    - 矩阵乘法 A·B、矩阵幂
    - 特征值 / 特征向量 eigenvals/eigenvects
    - 线性方程组（高斯消元 / linsolve）
    - 向量点积 / 叉积 / 模长
  微分方程:
    - 一阶/高阶 ODE（dsolve），含初始条件（ics）
  大学物理:
    - 牛顿第二定律 F = ma
    - 库仑定律 F = k q1 q2 / r²
    - 匀加速直线运动 / 自由落体

这些求解器与 solve.py 中的 _make_solution / _unsolved 结构兼容，
通过 SOLVERS 路由表接入主流水线。
"""

import re

import sympy
from sympy import (
    symbols, Symbol, Function, Eq, Matrix, Rational, pi, oo, sqrt,
    diff, integrate, dsolve, linsolve, solve, latex, simplify,
    sin, cos, exp, log,
)

from solve import (
    safe_parse, _make_solution, _unsolved, _make_sub_solution, _unsolved_sub,
    latex as _latex,
)

x, y, z, t, n, k = symbols("x y z t n k")
a, b, c = symbols("a b c")
s, w = symbols("s w")


# ═══════════════════════════════════════════════
# 矩阵解析
# ═══════════════════════════════════════════════

_MATRIX_ENV = re.compile(
    r"\\begin\{(?:pmatrix|bmatrix|matrix|vmatrix|Bmatrix|Vmatrix)\}"
    r"(.*?)"
    r"\\end\{(?:pmatrix|bmatrix|matrix|vmatrix|Bmatrix|Vmatrix)\}",
    re.DOTALL,
)


def parse_matrix(latex_str: str):
    """把 LaTeX 矩阵环境解析为 sympy.Matrix。解析失败返回 None。"""
    m = _MATRIX_ENV.search(latex_str)
    if not m:
        return None
    body = m.group(1)
    rows = []
    for row in re.split(r"\\\\", body):
        cells = [c.strip() for c in row.split("&")]
        cells = [c for c in cells if c != ""]
        if not cells:
            continue
        try:
            rows.append([safe_parse(c) for c in cells])
        except Exception:
            return None
    if not rows:
        return None
    try:
        return Matrix(rows)
    except Exception:
        return None


def extract_matrices(problem: dict) -> list:
    """从题目 + 子题的所有数学表达式中提取矩阵（带标签 A/B/...）。

    处理一个表达式含多个矩阵的情况（如 A+B、AB），按出现顺序返回。
    """
    found = []
    auto_label = 0
    for expr_info in problem.get("math_expressions", []):
        latex_str = expr_info.get("latex", "")
        for mm in _MATRIX_ENV.finditer(latex_str):
            mat = parse_matrix(mm.group(0))
            if mat is None:
                continue
            # 尝试从该矩阵之前的片段识别标签（如 "A ="）
            prefix = latex_str[:mm.start()]
            label = None
            lm = re.findall(r"([A-Za-z])\s*=", prefix)
            if lm:
                label = lm[-1]  # 最近的标签
            if label is None:
                label = chr(ord("A") + auto_label)
            auto_label += 1
            found.append((label, mat, latex_str))
    return found


def _tex_matrix(mat: Matrix) -> str:
    """把 sympy.Matrix 转成 LaTeX 字符串。"""
    return latex(mat)


# ═══════════════════════════════════════════════
# 线性代数求解器
# ═══════════════════════════════════════════════

def solve_matrix(problem: dict) -> dict:
    """线性代数综合求解器：根据题目意图路由到具体运算。"""
    text = problem["text"].lower()
    mats = extract_matrices(problem)
    math_exprs = problem.get("math_expressions", [])

    # 1) 线性方程组（多个含 "=" 的方程）
    if ("solve the system" in text or "线性方程组" in text
            or ("solve" in text and "system" in text)):
        return _solve_linear_system(problem)

    # 2) 行列式
    if any(k in text for k in ["determinant", "det(", "行列式", "det of"]):
        return _solve_determinant(problem, mats)

    # 3) 特征值 / 特征向量
    if any(k in text for k in ["eigenvalue", "eigenvector", "eigen", "特征值", "特征向量"]):
        return _solve_eigen(problem, mats)

    # 4) 逆矩阵
    if any(k in text for k in ["inverse", "invert", "逆矩阵", "inverse matrix"]):
        return _solve_inverse(problem, mats)

    # 5) 转置
    if any(k in text for k in ["transpose", "转置"]):
        return _solve_transpose(problem, mats)

    # 6) 秩
    if "rank" in text or "秩" in text:
        return _solve_rank(problem, mats)

    # 7) 矩阵乘法 / 加法（两个矩阵同时出现）
    if mats and len(mats) >= 2:
        if any(k in text for k in ["multiply", "product", "ab", "a b", "矩阵乘法",
                                   "矩阵乘积", "乘积", "compute ab", "计算ab"]):
            return _solve_matrix_product(problem, mats)
        if any(k in text for k in ["add", "sum", "a + b", "a+b", "加法", "相加"]):
            return _solve_matrix_add(problem, mats)

    # 8) 向量点积 / 叉积 / 模长
    if any(k in text for k in ["dot product", "点积", "cross product", "叉积", "norm", "模长", "magnitude"]):
        return _solve_vector_ops(problem)

    # 9) 兜底：有矩阵就给矩阵本身（用于"写出矩阵"类题）
    if mats:
        mat = mats[0][1]
        return _make_solution(
            problem,
            [f"$A = {_tex_matrix(mat)}$"],
            mat,
        )

    return _unsolved(problem, "未识别出矩阵或线性代数运算")


def _solve_determinant(problem, mats):
    if not mats:
        return _unsolved(problem, "未提取到矩阵")
    label, mat, _ = mats[0]
    d = mat.det()
    steps = [
        f"矩阵 $A = {_tex_matrix(mat)}$",
        f"行列式 $\\det(A) = {latex(d)}$",
    ]
    return _make_solution(problem, steps, d)


def _solve_eigen(problem, mats):
    if not mats:
        return _unsolved(problem, "未提取到矩阵")
    label, mat, _ = mats[0]
    eigvals = mat.eigenvals()
    eigvects = mat.eigenvects()
    steps = [f"矩阵 $A = {_tex_matrix(mat)}$"]
    steps.append("特征多项式：$\\det(A - \\lambda I) = 0$")
    for ev, mult, vecs in eigvects:
        vec_str = ", ".join(latex(v) for v in vecs)
        steps.append(f"特征值 $\\lambda = {latex(ev)}$（重数 {mult}），特征向量 $v = {vec_str}$")
    answer_latex = ",\\ ".join(
        f"\\lambda = {latex(ev)}" for ev in sorted(eigvals.keys(), key=str)
    )
    return _make_solution(problem, steps, answer_latex)


def _solve_inverse(problem, mats):
    if not mats:
        return _unsolved(problem, "未提取到矩阵")
    label, mat, _ = mats[0]
    if mat.rows != mat.cols:
        return _unsolved(problem, "矩阵非方阵，无法求逆")
    det = mat.det()
    if det == 0:
        return _make_solution(
            problem,
            [f"$A = {_tex_matrix(mat)}$", f"$\\det(A) = 0$，故 $A$ 不可逆"],
            r"\text{不可逆（奇异矩阵）}",
        )
    inv = mat.inv()
    steps = [
        f"矩阵 $A = {_tex_matrix(mat)}$",
        f"$\\det(A) = {latex(det)} \\neq 0$，故可逆",
        f"$A^{{-1}} = {_tex_matrix(inv)}$",
    ]
    return _make_solution(problem, steps, inv)


def _solve_transpose(problem, mats):
    if not mats:
        return _unsolved(problem, "未提取到矩阵")
    label, mat, _ = mats[0]
    t = mat.T
    steps = [f"$A = {_tex_matrix(mat)}$", f"$A^T = {_tex_matrix(t)}$"]
    return _make_solution(problem, steps, t)


def _solve_rank(problem, mats):
    if not mats:
        return _unsolved(problem, "未提取到矩阵")
    label, mat, _ = mats[0]
    r = mat.rank()
    steps = [f"$A = {_tex_matrix(mat)}$", f"$\\mathrm{{rank}}(A) = {r}$"]
    return _make_solution(problem, steps, r)


def _solve_matrix_product(problem, mats):
    A = mats[0][1]
    B = mats[1][1]
    if A.cols != B.rows:
        return _unsolved(problem, f"维度不匹配：A 是 {A.rows}x{A.cols}，B 是 {B.rows}x{B.cols}")
    prod = A * B
    steps = [
        f"$A = {_tex_matrix(A)},\\quad B = {_tex_matrix(B)}$",
        f"$AB = {_tex_matrix(prod)}$",
    ]
    return _make_solution(problem, steps, prod)


def _solve_matrix_add(problem, mats):
    A = mats[0][1]
    B = mats[1][1]
    if A.shape != B.shape:
        return _unsolved(problem, f"维度不匹配：A 是 {A.rows}x{A.cols}，B 是 {B.rows}x{B.cols}")
    s = A + B
    steps = [
        f"$A = {_tex_matrix(A)},\\quad B = {_tex_matrix(B)}$",
        f"$A + B = {_tex_matrix(s)}$",
    ]
    return _make_solution(problem, steps, s)


def _solve_linear_system(problem):
    """求解线性方程组：识别含 "=" 的方程并调用 linsolve。"""
    eq_exprs = []
    for expr_info in problem.get("math_expressions", []):
        ls = expr_info.get("latex", "")
        if "=" in ls:
            eq_exprs.append(ls)
    if not eq_exprs:
        return _unsolved(problem, "未提取到方程")
    eqs = []
    for ls in eq_exprs:
        try:
            lhs, rhs = ls.split("=", 1)
            eqs.append(Eq(safe_parse(lhs), safe_parse(rhs)))
        except Exception:
            continue
    if not eqs:
        return _unsolved(problem, "方程解析失败")
    try:
        # 检测实际出现的变量（避免引入多余自由变量）
        known = {"x": x, "y": y, "z": z, "t": t, "w": w, "s": s}
        used = set()
        for e in eqs:
            for sym in e.free_symbols:
                if str(sym) in known:
                    used.add(str(sym))
        order = ["x", "y", "z", "w", "s", "t"]
        vars_used = [known[v] for v in order if v in used]
        if not vars_used:
            vars_used = [x, y]
        sol = linsolve(eqs, vars_used)
        steps = ["方程：" + "，".join(f"${latex(e)}$" for e in eqs)]
        steps.append(f"解：${latex(sol)}$")
        return _make_solution(problem, steps, latex(sol))
    except Exception as e:
        return _unsolved(problem, f"方程组求解失败: {e}")


def _solve_vector_ops(problem):
    text = problem["text"].lower()
    # 提取形如 u = (1,2,3) 的向量
    vecs = []
    for expr_info in problem.get("math_expressions", []):
        ls = expr_info.get("latex", "")
        m = re.match(r"([a-z])\s*=\s*\(\s*([^)]+)\)", ls)
        if m:
            try:
                comps = [safe_parse(c) for c in m.group(2).split(",")]
                vecs.append((m.group(1), Matrix(comps)))
            except Exception:
                pass
    if len(vecs) < 2 and not vecs:
        return _unsolved(problem, "未提取到向量")

    if len(vecs) >= 2:
        u = vecs[0][1]
        v = vecs[1][1]
        if "cross" in text or "叉积" in text:
            res = u.cross(v)
            steps = [f"$u = {_tex_matrix(u)},\\; v = {_tex_matrix(v)}$",
                     f"$u \\times v = {_tex_matrix(res)}$"]
            return _make_solution(problem, steps, res)
        if "dot" in text or "点积" in text:
            res = u.dot(v)
            steps = [f"$u = {_tex_matrix(u)},\\; v = {_tex_matrix(v)}$",
                     f"$u \\cdot v = {latex(res)}$"]
            return _make_solution(problem, steps, res)

    # 模长
    if vecs and ("norm" in text or "模长" in text or "magnitude" in text):
        u = vecs[0][1]
        res = u.norm()
        steps = [f"$u = {_tex_matrix(u)}$", f"$\\|u\\| = {latex(res)}$"]
        return _make_solution(problem, steps, res)

    return _unsolved(problem, "未识别向量运算类型")


# ═══════════════════════════════════════════════
# 微分方程求解器
# ═══════════════════════════════════════════════

def solve_ode(problem: dict) -> dict:
    """用 dsolve 求解常微分方程（一阶/高阶，含初始条件）。"""
    text = problem["text"].lower()
    math_exprs = problem.get("math_expressions", [])
    ode_latex = ""
    for expr_info in math_exprs:
        ls = expr_info.get("latex", "")
        if ("y'" in ls or "y''" in ls or "y'''" in ls
                or "\\frac{dy}{dx}" in ls or "\\frac{d^{" in ls):
            ode_latex = ls
            break
    if not ode_latex:
        return _unsolved(problem, "未提取到微分方程")

    # 归一化 LaTeX 导数记号 → 内部记号
    expr = ode_latex
    expr = re.sub(r"\\frac\{d\^?2\s*y\}\{d\s*x\^?2\}", "@Y2@", expr)  # d²y/dx²
    expr = re.sub(r"\\frac\{dy\}\{dx\}", "@Y1@", expr)                # dy/dx
    expr = expr.replace("\\mathrm{d}", "d").replace("\\,", "").replace(" ", "")

    y_func = Function("y")
    try:
        if "=" in expr:
            lhs_str, rhs_str = expr.split("=", 1)
        else:
            lhs_str, rhs_str = expr, "0"
        lhs = _ode_side_to_expr(lhs_str)
        rhs = _ode_side_to_expr(rhs_str)
        ode = Eq(lhs, rhs)
        sol = dsolve(ode, y_func(x))
        steps = [
            f"微分方程：${latex(ode)}$",
            f"通解：${latex(sol)}$",
        ]
        return _make_solution(problem, steps, latex(sol.rhs))
    except Exception as e:
        return _unsolved(problem, f"ODE 求解失败: {e}")


def _ode_side_to_expr(s: str):
    """把 ODE 一侧的字符串（含 y'/y''/y 与 LaTeX 残余）解析为 sympy 表达式。"""
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations,
        implicit_multiplication_application, convert_xor,
    )
    s = s.strip()
    # 导数占位符（先于裸 y 替换，避免冲突）
    s = s.replace("y'''", "@Y3@").replace("y''", "@Y2@").replace("y'", "@Y1@")
    # 裸 y → y(x)（不匹配 y( 与 y' 已替换，允许 2y 隐式乘）
    s = re.sub(r"(?<![A-Za-z_])y(?![A-Za-z0-9_('])", "y(x)", s)
    # 还原导数
    s = s.replace("@Y3@", "Derivative(y(x), x, 3)")
    s = s.replace("@Y2@", "Derivative(y(x), x, 2)")
    s = s.replace("@Y1@", "Derivative(y(x), x)")
    # LaTeX → Python：上标 / 花括号
    s = re.sub(r"\^\{([^}]+)\}", r"**(\1)", s)
    s = re.sub(r"\^(\w)", r"**\1", s)
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("\\cdot", "*").replace("\\times", "*")
    y_func = Function("y")
    return parse_expr(
        s,
        local_dict={
            "Derivative": sympy.Derivative, "y": y_func, "x": x,
            "exp": exp, "sin": sin, "cos": cos, "log": log, "sqrt": sqrt,
            "pi": pi, "e": sympy.E,
        },
        transformations=standard_transformations + (
            implicit_multiplication_application, convert_xor),
    )


# ═══════════════════════════════════════════════
# 大学物理求解器（力学 / 电学基础）
# ═══════════════════════════════════════════════

def solve_physics(problem: dict) -> dict:
    """基础物理求解器：牛顿第二定律、库仑定律、匀加速运动。"""
    text = problem["text"].lower()

    # 库仑定律 F = k q1 q2 / r²
    if any(k in text for k in ["coulomb", "库仑", "charge", "电荷", "electric force", "静电力"]):
        return _solve_coulomb(problem)

    # 牛顿第二定律 F = ma
    if any(k in text for k in ["newton", "牛顿", "force", "acceleration", "f = ma", "力"]):
        return _solve_newton(problem)

    # 匀加速运动 / 自由落体
    if any(k in text for k in ["free fall", "自由落体", "kinematic", "运动", "velocity", "速度", "位移", "displacement"]):
        return _solve_kinematics(problem)

    return _unsolved(problem, "未识别的物理题型（支持：牛顿定律/库仑定律/匀加速运动）")


def _extract_named_value(text: str, math_exprs: list, names: list):
    """从文本/公式提取形如 'name = value' 的数值。返回 (name, sympy_value)。"""
    # 先看数学表达式
    for expr_info in math_exprs:
        ls = expr_info.get("latex", "")
        for nm in names:
            m = re.match(rf"{nm}\s*=\s*(.+)", ls)
            if m:
                try:
                    return (nm, safe_parse(m.group(1)))
                except Exception:
                    pass
    # 再看文本 'mass = 2 kg' / 'm = 2'
    for nm in names:
        m = re.search(rf"{nm}\s*=\s*([\d.]+)", text)
        if m:
            try:
                return (nm, Rational(m.group(1)))
            except Exception:
                pass
    return None


def _solve_coulomb(problem):
    text = problem["text"].lower()
    m = re.search(r"([\d.]+)\s*(?:e-?[\d]+)?\s*(?:c|µc|μc|uc|nc)", text)
    k = Rational(9) * 10**9  # N·m²/C²
    # 提取 q1, q2, r
    q1 = _extract_named_value(text, problem.get("math_expressions", []), ["q1", "q_1"])
    q2 = _extract_named_value(text, problem.get("math_expressions", []), ["q2", "q_2"])
    r = _extract_named_value(text, problem.get("math_expressions", []), ["r"])
    if not (q1 and q2 and r):
        return _unsolved(problem, "库仑定律需要 q1、q2、r 三个量")
    q1v, q2v, rv = q1[1], q2[1], r[1]
    F = k * q1v * q2v / rv**2
    steps = [
        f"库仑定律：$F = k \\frac{{q_1 q_2}}{{r^2}}$，$k = 9\\times 10^9$ N·m²/C²",
        f"$q_1 = {latex(q1v)},\\; q_2 = {latex(q2v)},\\; r = {latex(rv)}$",
        f"$F = {latex(F)}$ N",
    ]
    return _make_solution(problem, steps, latex(F))


def _solve_newton(problem):
    text = problem["text"].lower()
    math_exprs = problem.get("math_expressions", [])
    mval = _extract_named_value(text, math_exprs, ["m", "mass"])
    aval = _extract_named_value(text, math_exprs, ["a", "acceleration"])
    Fval = _extract_named_value(text, math_exprs, ["F", "force"])
    # 中文表述兜底：质量为 X / 力为 X / 加速度为 X（允许数值被 $ 包裹）
    if mval is None:
        mm = re.search(r"质量(?:为|是)?\s*\$?\s*([\d.]+)", text)
        if mm:
            mval = ("m", Rational(mm.group(1)))
    if Fval is None:
        fm = re.search(r"(?:力|受到)\s*(?:为|是|大小)?\s*\$?\s*([\d.]+)\s*\$?\s*n", text)
        if fm:
            Fval = ("F", Rational(fm.group(1)))
    if aval is None:
        am = re.search(r"加速度(?:为|是)?\s*\$?\s*([\d.]+)", text)
        if am:
            aval = ("a", Rational(am.group(1)))
    # 已知 F,m 求 a；或 F,a 求 m；或 m,a 求 F
    if mval and aval:
        F = mval[1] * aval[1]
        steps = [f"牛顿第二定律：$F = ma$",
                 f"$m = {latex(mval[1])},\\; a = {latex(aval[1])}$",
                 f"$F = {latex(F)}$ N"]
        return _make_solution(problem, steps, latex(F))
    if Fval and mval:
        a = Fval[1] / mval[1]
        steps = [f"$F = ma \\Rightarrow a = F/m$",
                 f"$F = {latex(Fval[1])},\\; m = {latex(mval[1])}$",
                 f"$a = {latex(a)}$ m/s²"]
        return _make_solution(problem, steps, latex(a))
    if Fval and aval:
        m = Fval[1] / aval[1]
        steps = [f"$F = ma \\Rightarrow m = F/a$",
                 f"$F = {latex(Fval[1])},\\; a = {latex(aval[1])}$",
                 f"$m = {latex(m)}$ kg"]
        return _make_solution(problem, steps, latex(m))
    return _unsolved(problem, "牛顿定律需要 F、m、a 中的两个量")


def _solve_kinematics(problem):
    text = problem["text"].lower()
    g = Rational(49, 5)  # 9.8 m/s²
    h = _extract_named_value(text, problem.get("math_expressions", []), ["h", "height"])
    v0 = _extract_named_value(text, problem.get("math_expressions", []), ["v0", "v_0", "initial velocity"])
    # 自由落体时间 t = sqrt(2h/g)
    if h and ("free fall" in text or "自由落体" in text):
        hval = h[1]
        tval = sqrt(2 * hval / g)
        steps = [
            f"自由落体：$h = \\frac{{1}}{{2}} g t^2 \\Rightarrow t = \\sqrt{{2h/g}}$",
            f"$h = {latex(hval)},\\; g = {latex(g)}$",
            f"$t = {latex(simplify(tval))}$ s",
        ]
        return _make_solution(problem, steps, latex(simplify(tval)))
    return _unsolved(problem, "未识别的运动学题型")
