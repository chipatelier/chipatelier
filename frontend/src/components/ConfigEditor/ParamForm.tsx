import { CURATED_PARAMS } from "./ParamMetadata";

interface ParamFormProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  lockedParams: Record<string, string>;
  editableParams: string[]; // empty = all curated params editable
}

export function ParamForm({
  values,
  onChange,
  lockedParams,
  editableParams,
}: ParamFormProps) {
  const visibleParams =
    editableParams.length > 0
      ? CURATED_PARAMS.filter(
          (p) => editableParams.includes(p.key) || p.key in lockedParams
        )
      : CURATED_PARAMS;

  return (
    <div className="param-form space-y-4 p-4">
      {visibleParams.map((param) => {
        const isLocked = param.key in lockedParams;
        const value = isLocked
          ? lockedParams[param.key]
          : (values[param.key] ?? "");
        return (
          <div key={param.key} className="param-row flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <label
                htmlFor={`param-${param.key}`}
                className="font-medium text-sm"
              >
                {param.label}
              </label>
              {isLocked && (
                <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                  Locked by instructor
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <input
                id={`param-${param.key}`}
                type="number"
                min={param.min}
                max={param.max}
                step="any"
                value={value}
                disabled={isLocked}
                onChange={(e) =>
                  !isLocked && onChange(param.key, e.target.value)
                }
                className={`border rounded px-2 py-1 w-32 ${
                  isLocked
                    ? "bg-gray-100 text-gray-500 cursor-not-allowed"
                    : ""
                }`}
                aria-label={param.label}
              />
              {param.unit && (
                <span className="text-xs text-gray-500">{param.unit}</span>
              )}
              <span className="text-xs text-gray-400">
                {param.min}–{param.max}
              </span>
            </div>
            <p className="text-xs text-gray-500">{param.description}</p>
          </div>
        );
      })}
    </div>
  );
}
