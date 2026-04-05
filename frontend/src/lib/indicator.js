import { ratingSortValue } from "./ratings.js";

const FIELD_DEFINITIONS = [
  { key: "annual_yield", label: "Аннуализированная доходность" },
  { key: "bond_annual_yield", label: "Годовая доходность облигации" },
  { key: "horizon_yield", label: "До горизонта" },
  { key: "price", label: "Цена" },
  { key: "coupon_percent", label: "Купон, %" },
  { key: "coupons_per_year", label: "Купонов в год" },
  { key: "months_to_maturity", label: "Месяцев до погашения" },
  { key: "rating_score", label: "Рейтинг-скор" },
];

const FUNCTION_DEFINITIONS = [
  { token: "log(", label: "log(" },
  { token: "sqrt(", label: "sqrt(" },
  { token: "abs(", label: "abs(" },
  { token: "exp(", label: "exp(" },
  { token: "min(", label: "min(" },
  { token: "max(", label: "max(" },
  { token: "pow(", label: "pow(" },
];

const FIELD_GETTERS = {
  annual_yield: (bond) => Number(bond.annual_yield),
  bond_annual_yield: (bond) => Number(bond.bond_annual_yield),
  horizon_yield: (bond) => Number(bond.yield_to_horizon),
  price: (bond) => Number(bond.price),
  coupon_percent: (bond) => Number(bond.coupon_percent),
  coupons_per_year: (bond) => Number(bond.coupons_per_year),
  months_to_maturity: (bond) => Number(bond.months_to_maturity),
  rating_score: (bond) => Number(ratingSortValue(bond.rating)),
};

const FUNCTION_ARITY = {
  abs: 1,
  exp: 1,
  log: 1,
  max: 2,
  min: 2,
  pow: 2,
  sqrt: 1,
};

const IDENTIFIER_RE = /[A-Za-z_]/;
const IDENTIFIER_BODY_RE = /[A-Za-z0-9_]/;

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

export const INDICATOR_FIELD_BLOCKS = FIELD_DEFINITIONS.map(({ key, label }) => ({
  token: key,
  label,
}));

export const INDICATOR_OPERATOR_BLOCKS = [
  { token: "+", label: "+" },
  { token: "-", label: "-" },
  { token: "*", label: "×" },
  { token: "/", label: "÷" },
  { token: "(", label: "(" },
  { token: ")", label: ")" },
  { token: ",", label: "," },
];

export const INDICATOR_FUNCTION_BLOCKS = FUNCTION_DEFINITIONS;

export const INDICATOR_DERIVATIVE_BLOCKS = FIELD_DEFINITIONS.filter(
  ({ key }) => key !== "rating_score",
).map(({ key, label }) => ({
  token: `diff_${key}(`,
  label: `d/d ${label}`,
}));

function isDigit(char) {
  return char >= "0" && char <= "9";
}

function tokenize(input) {
  const tokens = [];
  let cursor = 0;
  while (cursor < input.length) {
    const current = input[cursor];
    if (/\s/.test(current)) {
      cursor += 1;
      continue;
    }
    if ("()+-*/,".includes(current)) {
      tokens.push({ type: current, value: current });
      cursor += 1;
      continue;
    }
    if (isDigit(current) || current === ".") {
      let end = cursor + 1;
      while (end < input.length && (isDigit(input[end]) || input[end] === ".")) {
        end += 1;
      }
      const raw = input.slice(cursor, end);
      if (raw === ".") {
        throw new Error("Некорректное число в формуле.");
      }
      tokens.push({ type: "number", value: raw });
      cursor = end;
      continue;
    }
    if (IDENTIFIER_RE.test(current)) {
      let end = cursor + 1;
      while (end < input.length && IDENTIFIER_BODY_RE.test(input[end])) {
        end += 1;
      }
      tokens.push({ type: "identifier", value: input.slice(cursor, end) });
      cursor = end;
      continue;
    }
    throw new Error(`Недопустимый символ: ${current}`);
  }
  return tokens;
}

function createParser(tokens) {
  let index = 0;

  function peek(offset = 0) {
    return tokens[index + offset] ?? null;
  }

  function consume(expectedType = null) {
    const token = peek();
    if (!token) {
      throw new Error("Формула обрывается раньше времени.");
    }
    if (expectedType && token.type !== expectedType) {
      throw new Error(`Ожидался токен ${expectedType}, получен ${token.type}.`);
    }
    index += 1;
    return token;
  }

  function parseExpression() {
    let node = parseTerm();
    while (peek()?.type === "+" || peek()?.type === "-") {
      const operator = consume().type;
      node = {
        type: "binary",
        operator,
        left: node,
        right: parseTerm(),
      };
    }
    return node;
  }

  function parseTerm() {
    let node = parseUnary();
    while (peek()?.type === "*" || peek()?.type === "/") {
      const operator = consume().type;
      node = {
        type: "binary",
        operator,
        left: node,
        right: parseUnary(),
      };
    }
    return node;
  }

  function parseUnary() {
    const token = peek();
    if (!token) {
      throw new Error("Пустая формула.");
    }
    if (token.type === "+") {
      consume("+");
      return parseUnary();
    }
    if (token.type === "-") {
      consume("-");
      return { type: "unary", operator: "-", argument: parseUnary() };
    }
    return parsePrimary();
  }

  function parseFunctionCall(name) {
    const isDerivative = name.startsWith("diff_") && hasOwn(FIELD_GETTERS, name.slice(5));
    if (!isDerivative && !hasOwn(FUNCTION_ARITY, name)) {
      throw new Error(`Неизвестная функция: ${name}`);
    }
    consume("(");
    const args = [];
    if (peek()?.type !== ")") {
      args.push(parseExpression());
      while (peek()?.type === ",") {
        consume(",");
        args.push(parseExpression());
      }
    }
    consume(")");
    if (isDerivative && args.length !== 1) {
      throw new Error(`Функция ${name} принимает ровно один аргумент.`);
    }
    if (!isDerivative && args.length !== FUNCTION_ARITY[name]) {
      throw new Error(`Функция ${name} ожидает ${FUNCTION_ARITY[name]} аргумент(а).`);
    }
    return { type: "function", name, args };
  }

  function parsePrimary() {
    const token = peek();
    if (!token) {
      throw new Error("Пустая формула.");
    }
    if (token.type === "number") {
      consume("number");
      return { type: "number", value: Number(token.value) };
    }
    if (token.type === "identifier") {
      const name = consume("identifier").value;
      if (peek()?.type === "(") {
        return parseFunctionCall(name);
      }
      if (!hasOwn(FIELD_GETTERS, name)) {
        throw new Error(`Неизвестный блок: ${name}`);
      }
      return { type: "variable", name };
    }
    if (token.type === "(") {
      consume("(");
      const node = parseExpression();
      consume(")");
      return node;
    }
    throw new Error(`Неожиданный токен: ${token.value}`);
  }

  const ast = parseExpression();
  if (peek() !== null) {
    throw new Error(`Лишний токен в конце формулы: ${peek().value}`);
  }
  return ast;
}

function buildContext(bond) {
  const context = {};
  for (const [key, getter] of Object.entries(FIELD_GETTERS)) {
    context[key] = getter(bond);
  }
  return context;
}

function evaluateFunction(name, args) {
  switch (name) {
    case "abs":
      return Math.abs(args[0]);
    case "exp":
      return Math.exp(args[0]);
    case "log":
      return args[0] > 0 ? Math.log(args[0]) : Number.NaN;
    case "max":
      return Math.max(args[0], args[1]);
    case "min":
      return Math.min(args[0], args[1]);
    case "pow":
      return Math.pow(args[0], args[1]);
    case "sqrt":
      return args[0] >= 0 ? Math.sqrt(args[0]) : Number.NaN;
    default:
      return Number.NaN;
  }
}

function evaluateAst(node, context) {
  switch (node.type) {
    case "number":
      return node.value;
    case "variable":
      return context[node.name];
    case "unary": {
      const value = evaluateAst(node.argument, context);
      return node.operator === "-" ? -value : value;
    }
    case "binary": {
      const left = evaluateAst(node.left, context);
      const right = evaluateAst(node.right, context);
      if (!Number.isFinite(left) || !Number.isFinite(right)) {
        return Number.NaN;
      }
      switch (node.operator) {
        case "+":
          return left + right;
        case "-":
          return left - right;
        case "*":
          return left * right;
        case "/":
          return right === 0 ? Number.NaN : left / right;
        default:
          return Number.NaN;
      }
    }
    case "function": {
      if (node.name.startsWith("diff_")) {
        const variable = node.name.slice(5);
        if (!hasOwn(context, variable)) {
          return Number.NaN;
        }
        const origin = Number(context[variable]);
        if (!Number.isFinite(origin)) {
          return Number.NaN;
        }
        const step = Math.max(Math.abs(origin) * 1e-4, 1e-4);
        const leftContext = { ...context, [variable]: origin - step };
        const rightContext = { ...context, [variable]: origin + step };
        const left = evaluateAst(node.args[0], leftContext);
        const right = evaluateAst(node.args[0], rightContext);
        if (!Number.isFinite(left) || !Number.isFinite(right)) {
          return Number.NaN;
        }
        return (right - left) / (2 * step);
      }

      const arity = FUNCTION_ARITY[node.name];
      if (!arity) {
        return Number.NaN;
      }
      if (node.args.length !== arity) {
        return Number.NaN;
      }
      const values = node.args.map((arg) => evaluateAst(arg, context));
      if (values.some((value) => !Number.isFinite(value))) {
        return Number.NaN;
      }
      return evaluateFunction(node.name, values);
    }
    default:
      return Number.NaN;
  }
}

export function tokensToFormula(tokens) {
  return tokens.join(" ").trim();
}

export function parseIndicator(expr) {
  const normalized = String(expr || "").trim();
  if (!normalized) {
    throw new Error("Добавьте блоки для формулы.");
  }
  return createParser(tokenize(normalized));
}

export function compileIndicator(expr) {
  const ast = parseIndicator(expr);
  return (bond) => {
    const result = evaluateAst(ast, buildContext(bond));
    return Number.isFinite(result) ? result : Number.NaN;
  };
}

export function evalIndicator(expr, bond) {
  try {
    return compileIndicator(expr)(bond);
  } catch {
    return Number.NaN;
  }
}
