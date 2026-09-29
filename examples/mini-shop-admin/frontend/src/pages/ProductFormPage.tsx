import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createProduct, getProduct, updateProduct } from '../api/products'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { ProductImage } from '../components/ProductImage'
import type { ProductPayload } from '../types/product'

interface FormState {
  name: string
  main_image_url: string
  price: string
  stock: string
  description: string
}

const emptyForm: FormState = {
  name: '',
  main_image_url: '',
  price: '',
  stock: '',
  description: '',
}

function validate(form: FormState) {
  const errors: Record<string, string> = {}
  if (!form.name.trim()) errors.name = '请输入商品名称'
  if (!form.main_image_url.trim()) {
    errors.main_image_url = '请输入主图 URL'
  } else {
    try {
      const url = new URL(form.main_image_url.trim())
      if (!['http:', 'https:'].includes(url.protocol)) throw new Error()
    } catch {
      errors.main_image_url = '主图 URL 必须是有效的 http 或 https 地址'
    }
  }
  if (!/^\d+(\.\d{1,2})?$/.test(form.price) || Number(form.price) <= 0) {
    errors.price = '售价必须大于 0，且最多保留两位小数'
  }
  if (!/^\d+$/.test(form.stock)) {
    errors.stock = '库存必须为大于等于 0 的整数'
  }
  return errors
}

export function ProductFormPage() {
  const { id } = useParams()
  const editing = Boolean(id)
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(emptyForm)
  const [initial, setInitial] = useState<FormState>(emptyForm)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [confirmLeave, setConfirmLeave] = useState(false)
  const inputs = useRef<Record<string, HTMLElement | null>>({})

  const dirty = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(initial),
    [form, initial],
  )

  const load = async () => {
    if (!id) return
    setLoading(true)
    setLoadError('')
    try {
      const product = await getProduct(id)
      const value = {
        name: product.name,
        main_image_url: product.main_image_url,
        price: product.price,
        stock: String(product.stock),
        description: product.description || '',
      }
      setForm(value)
      setInitial(value)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '商品信息加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    document.title = `${editing ? '编辑商品' : '新建商品'} - Mini Shop Admin`
    if (editing) void load()
  }, [id])

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (dirty && !saving) event.preventDefault()
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [dirty, saving])

  const change = (key: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, [key]: '' }))
  }

  const leave = () => {
    if (dirty) setConfirmLeave(true)
    else navigate('/products')
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const nextErrors = validate(form)
    setErrors(nextErrors)
    setSaveError('')
    const first = Object.keys(nextErrors)[0]
    if (first) {
      inputs.current[first]?.focus()
      return
    }

    const payload: ProductPayload = {
      name: form.name.trim(),
      main_image_url: form.main_image_url.trim(),
      price: Number(form.price).toFixed(2),
      stock: Number(form.stock),
      description: form.description.trim() || null,
    }

    setSaving(true)
    try {
      if (editing && id) await updateProduct(id, payload)
      else await createProduct(payload)
      setInitial(form)
      navigate('/products', { replace: true })
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : '商品保存失败')
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <>
        <div className="page-title-row"><h1>{editing ? '编辑商品' : '新建商品'}</h1></div>
        <div className="form-skeleton" role="status">正在加载商品信息</div>
      </>
    )
  }

  if (loadError) {
    return (
      <div className="page-error">
        <h1>商品信息加载失败</h1>
        <p>{loadError}</p>
        <div>
          <button className="button primary" onClick={() => void load()}>重试</button>
          <button className="button secondary" onClick={() => navigate('/products')}>返回商品列表</button>
        </div>
      </div>
    )
  }

  return (
    <>
      <button className="back-link" onClick={leave}>← 返回商品列表</button>
      <div className="page-title-row">
        <div>
          <h1>{editing ? '编辑商品' : '新建商品'}</h1>
          <p>{editing ? '修改商品资料、价格和库存' : '创建后商品默认为下架'}</p>
        </div>
      </div>
      {saveError && <div className="alert danger form-alert">{saveError}</div>}

      <form className="product-form" onSubmit={submit} noValidate>
        <section className="form-section">
          <h2>基本信息</h2>
          <div className="form-row">
            <label htmlFor="product-name">商品名称 <b>*</b></label>
            <div>
              <input
                id="product-name"
                ref={(node) => { inputs.current.name = node }}
                maxLength={200}
                value={form.name}
                disabled={saving}
                aria-invalid={Boolean(errors.name)}
                onChange={(event) => change('name', event.target.value)}
              />
              <span className="field-error">{errors.name}</span>
            </div>
          </div>
          <div className="form-row">
            <label htmlFor="main-image">主图 URL <b>*</b></label>
            <div className="image-form-control">
              <div>
                <input
                  id="main-image"
                  ref={(node) => { inputs.current.main_image_url = node }}
                  maxLength={2048}
                  value={form.main_image_url}
                  disabled={saving}
                  aria-invalid={Boolean(errors.main_image_url)}
                  onChange={(event) => change('main_image_url', event.target.value)}
                />
                <span className="field-error">{errors.main_image_url}</span>
              </div>
              <ProductImage
                src={form.main_image_url}
                alt="商品主图预览"
                className="image-preview"
              />
            </div>
          </div>
          <div className="form-row">
            <label htmlFor="description">商品描述</label>
            <div>
              <textarea
                id="description"
                maxLength={10000}
                value={form.description}
                disabled={saving}
                onChange={(event) => change('description', event.target.value)}
              />
              <div className="character-count">{form.description.length} 字</div>
            </div>
          </div>
        </section>

        <section className="form-section">
          <h2>销售与库存</h2>
          <div className="form-row">
            <label htmlFor="price">售价 <b>*</b></label>
            <div>
              <div className="money-input">
                <span>¥</span>
                <input
                  id="price"
                  ref={(node) => { inputs.current.price = node }}
                  type="number"
                  min="0.01"
                  max="99999999.99"
                  step="0.01"
                  value={form.price}
                  disabled={saving}
                  aria-invalid={Boolean(errors.price)}
                  onWheel={(event) => event.currentTarget.blur()}
                  onChange={(event) => change('price', event.target.value)}
                />
              </div>
              <span className="field-error">{errors.price}</span>
            </div>
          </div>
          <div className="form-row">
            <label htmlFor="stock">库存 <b>*</b></label>
            <div>
              <input
                id="stock"
                className="short-input"
                ref={(node) => { inputs.current.stock = node }}
                type="number"
                min="0"
                step="1"
                value={form.stock}
                disabled={saving}
                aria-invalid={Boolean(errors.stock)}
                onWheel={(event) => event.currentTarget.blur()}
                onChange={(event) => change('stock', event.target.value)}
              />
              <span className="field-error">{errors.stock}</span>
            </div>
          </div>
        </section>

        <div className="sticky-actions">
          <button className="button secondary" type="button" disabled={saving} onClick={leave}>
            取消
          </button>
          <button className="button primary" disabled={saving}>
            {saving && <span className="spinner small" />}
            {saving ? '保存中' : editing ? '保存修改' : '创建商品'}
          </button>
        </div>
      </form>

      <ConfirmDialog
        open={confirmLeave}
        title="放弃未保存的修改？"
        message="当前表单包含未保存内容，离开后这些内容将丢失。"
        confirmText="放弃并离开"
        danger
        onClose={() => setConfirmLeave(false)}
        onConfirm={() => navigate('/products')}
      />
    </>
  )
}
